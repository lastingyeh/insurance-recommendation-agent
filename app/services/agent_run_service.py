from __future__ import annotations

from datetime import datetime
from collections.abc import AsyncGenerator

from google.adk.events.event import Event
from google.adk.runners import Runner
from google.genai import types as genai_types

from app.config import AppRuntimeConfig
from app.services.session_service import SessionService, safe_stringify


def format_event_timestamp(timestamp: float | None) -> str:
    value = datetime.fromtimestamp(timestamp) if timestamp else datetime.now()
    return value.strftime("%H:%M")


def stringify_state_patch(state_delta: dict[str, object]) -> dict[str, str]:
    return {key: safe_stringify(value) for key, value in state_delta.items()}


def is_echoed_user_input(event: Event, prompt: str) -> bool:
    if event.author != "user" or not event.content or not event.content.parts:
        return False

    if any(part.function_response for part in event.content.parts):
        return False

    if any(part.function_call for part in event.content.parts):
        return False

    normalized_prompt = prompt.strip()
    return any(
        (part.text or "").strip() == normalized_prompt for part in event.content.parts
    )


def build_user_message_content(prompt: str) -> genai_types.Content:
    return genai_types.Content(
        role="user",
        parts=[genai_types.Part(text=prompt)],
    )


async def iter_run_events(
    runner: Runner,
    *,
    user_id: str,
    session_id: str,
    prompt: str,
    state_delta: dict[str, str] | None = None,
) -> AsyncGenerator[Event, None]:
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=build_user_message_content(prompt),
        state_delta=state_delta or None,
    ):
        yield event


def build_meta_envelope() -> dict[str, object]:
    return {
        "type": "meta",
        "transport": "proxy",
        "notice": "目前由 FastAPI backend 直接代理 ADK Runner（SSE）。",
    }


def build_done_envelope(final_text: str, state: dict[str, str]) -> dict[str, object]:
    return {
        "type": "done",
        "finalText": final_text,
        "state": state,
    }


def build_error_envelope(message: str) -> dict[str, object]:
    return {
        "type": "error",
        "message": message,
    }


def merge_state_patches(
    current_state: dict[str, str],
    envelopes: list[dict[str, object]],
) -> dict[str, str]:
    merged_state = dict(current_state)
    for envelope in envelopes:
        if envelope.get("type") == "state":
            patch = envelope.get("patch", {})
            if isinstance(patch, dict):
                merged_state.update(
                    {str(key): str(value) for key, value in patch.items()}
                )
    return merged_state


def map_adk_event_to_envelopes(event: Event, sequence: int) -> list[dict[str, object]]:
    event_id = event.id or f"evt-fastapi-{sequence}"
    timestamp = format_event_timestamp(event.timestamp)
    envelopes: list[dict[str, object]] = []
    parts = event.content.parts if event.content and event.content.parts else []

    for part_index, part in enumerate(parts):
        suffix = f"{event_id}-{part_index}"

        if part.function_call and part.function_call.name:
            envelopes.append(
                {
                    "type": "timeline",
                    "event": {
                        "id": f"{suffix}-call",
                        "kind": "tool-call",
                        "title": part.function_call.name,
                        "summary": f"ADK 請求工具 {part.function_call.name}",
                        "timestamp": timestamp,
                        "payload": [
                            f"args: {safe_stringify(part.function_call.args or {})}",
                            f"author: {event.author or 'agent'}",
                        ],
                    },
                }
            )

        if part.function_response and part.function_response.name:
            envelopes.append(
                {
                    "type": "timeline",
                    "event": {
                        "id": f"{suffix}-result",
                        "kind": "tool-result",
                        "title": f"{part.function_response.name} result",
                        "summary": f"工具 {part.function_response.name} 已回傳結果",
                        "timestamp": timestamp,
                        "payload": [
                            f"response: {safe_stringify(part.function_response.response or {})}"
                        ],
                    },
                }
            )

        text = (part.text or "").strip()
        if text and event.author != "user":
            envelopes.append(
                {
                    "type": "timeline",
                    "event": {
                        "id": f"{suffix}-{'stream' if event.partial else 'agent'}",
                        "kind": "stream" if event.partial else "agent",
                        "title": (
                            "partial_response" if event.partial else "agent_response"
                        ),
                        "summary": text,
                        "timestamp": timestamp,
                        "payload": [
                            text,
                            f"author: {event.author or 'agent'}",
                            f"partial: {'true' if event.partial else 'false'}",
                        ],
                    },
                }
            )
            envelopes.append(
                {
                    "type": "message",
                    "text": text,
                    "mode": "append" if event.partial else "replace",
                    "final": not bool(event.partial),
                }
            )

    if event.actions and event.actions.state_delta:
        patch = stringify_state_patch(event.actions.state_delta)
        envelopes.append(
            {
                "type": "timeline",
                "event": {
                    "id": f"{event_id}-state",
                    "kind": "state",
                    "title": "state_delta",
                    "summary": "ADK session state 已更新",
                    "timestamp": timestamp,
                    "payload": [f"{key}: {value}" for key, value in patch.items()],
                },
            }
        )
        envelopes.append({"type": "state", "patch": patch})

    return envelopes


class AgentRunService:
    def __init__(
        self,
        runner: Runner,
        sessions: SessionService,
        config: AppRuntimeConfig,
    ) -> None:
        self._runner = runner
        self._sessions = sessions
        self._config = config

    async def ensure_session(
        self,
        session_id: str,
        initial_state: dict[str, str] | None = None,
        user_id: str | None = None,
    ) -> None:
        await self._sessions.ensure_session(session_id, initial_state, user_id=user_id)

    async def stream(
        self,
        *,
        prompt: str,
        session_id: str,
        session_state: dict[str, str] | None = None,
        user_id: str | None = None,
    ) -> AsyncGenerator[dict[str, object], None]:
        sequence = 0
        current_text = ""
        merged_state = dict(session_state or {})
        resolved_user_id = (
            user_id.strip() if user_id and user_id.strip() else self._config.api_user_id
        )

        yield build_meta_envelope()

        try:
            async for event in iter_run_events(
                self._runner,
                user_id=resolved_user_id,
                session_id=session_id,
                prompt=prompt,
                state_delta=session_state,
            ):
                if is_echoed_user_input(event, prompt):
                    continue

                sequence += 1
                envelopes = map_adk_event_to_envelopes(event, sequence)
                merged_state = merge_state_patches(merged_state, envelopes)

                for envelope in envelopes:
                    if envelope.get("type") == "message":
                        text = str(envelope.get("text", ""))
                        if envelope.get("mode") == "append":
                            current_text += text
                        else:
                            current_text = text

                    yield envelope

            final_state = await self._sessions.get_state(
                session_id=session_id,
                fallback_state=merged_state,
                user_id=user_id,
            )
            yield build_done_envelope(
                final_text=current_text
                or "ADK runtime 已完成執行，請查看右側 event history。",
                state=final_state,
            )
        except Exception as exc:
            yield build_error_envelope(str(exc))
