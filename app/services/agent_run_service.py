"""
Agent 執行服務模組。
負責與 Google ADK (Agent Development Kit) Runner 互動，處理 AI Agent 的執行流程、串流回應、狀態更新及事件轉換。
"""

from __future__ import annotations

from datetime import datetime
from collections.abc import AsyncGenerator

from google.adk.events.event import Event
from google.adk.runners import Runner
from google.genai import types as genai_types

from app.config import AppRuntimeConfig
from app.services.session_service import SessionService, safe_stringify


def format_event_timestamp(timestamp: float | None) -> str:
    """
    格式化事件的時間戳記。

    Args:
        timestamp: Unix 時間戳記，若為 None 則使用目前時間。

    Returns:
        格式化後的時分字串 (例如 "14:30")。
    """
    value = datetime.fromtimestamp(timestamp) if timestamp else datetime.now()
    return value.strftime("%H:%M")


def stringify_state_patch(state_delta: dict[str, object]) -> dict[str, str]:
    """
    將狀態更新字典中的所有值轉換為字串。

    Args:
        state_delta: 包含狀態變動的原始字典。

    Returns:
        所有值皆轉換為字串後的字典。
    """
    return {key: safe_stringify(value) for key, value in state_delta.items()}


def is_echoed_user_input(event: Event, prompt: str) -> bool:
    """
    判斷 ADK 事件是否為使用者輸入的回顯 (Echo)。

    Args:
        event: ADK 事件對象。
        prompt: 使用者的原始輸入提示字串。

    Returns:
        True 代表該事件僅是回顯使用者的輸入，通常應在前端顯示時過濾。
    """
    if event.author != "user" or not event.content or not event.content.parts:
        return False

    # 如果包含工具回傳結果或工具調用，則不視為單純的回顯
    if any(part.function_response for part in event.content.parts):
        return False

    if any(part.function_call for part in event.content.parts):
        return False

    normalized_prompt = prompt.strip()
    return any(
        (part.text or "").strip() == normalized_prompt for part in event.content.parts
    )


def build_user_message_content(prompt: str) -> genai_types.Content:
    """
    建立符合 Google GenAI 類型的使用者訊息內容。

    Args:
        prompt: 使用者輸入的文字。

    Returns:
        封裝好的 genai_types.Content 物件。
    """
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
    """
    非同步迭代 ADK Runner 的執行事件。

    Args:
        runner: ADK Runner 實例。
        user_id: 使用者 ID。
        session_id: 對話視窗 ID。
        prompt: 使用者輸入提示。
        state_delta: 欲傳遞給 Agent 的初始狀態變動。

    Yields:
        ADK 執行過程中產生的事件 (Event)。
    """
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=build_user_message_content(prompt),
        state_delta=state_delta or None,
    ):
        yield event


def build_meta_envelope() -> dict[str, object]:
    """
    建立中繼資料 (Meta) 封包，用於串流開始時告知前端傳輸層資訊。
    """
    return {
        "type": "meta",
        "transport": "proxy",
        "notice": "目前由 FastAPI backend 直接代理 ADK Runner（SSE）。",
    }


def build_done_envelope(final_text: str, state: dict[str, str]) -> dict[str, object]:
    """
    建立執行完成 (Done) 封包。

    Args:
        final_text: Agent 最終回傳的完整回覆文字。
        state: 對話結束後的最終 session 狀態。
    """
    return {
        "type": "done",
        "finalText": final_text,
        "state": state,
    }


def build_error_envelope(message: str) -> dict[str, object]:
    """
    建立錯誤 (Error) 封包。

    Args:
        message: 錯誤訊息內容。
    """
    return {
        "type": "error",
        "message": message,
    }


def merge_state_patches(
    current_state: dict[str, str],
    envelopes: list[dict[str, object]],
) -> dict[str, str]:
    """
    將新產生的狀態封包合併至目前的狀態字典中。

    Args:
        current_state: 現有的狀態字典。
        envelopes: 本次事件產生的封包列表。

    Returns:
        合併後的新狀態字典。
    """
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
    """
    將 ADK 原始事件轉換為前端可識別的封包 (Envelopes) 列表。
    處理文字串流、工具調用 (Tool Call)、工具結果 (Tool Result) 及狀態變動。

    Args:
        event: ADK 原始事件。
        sequence: 序列號，用於生成唯一的事件 ID。

    Returns:
        轉換後的封包列表。
    """
    event_id = event.id or f"evt-fastapi-{sequence}"
    timestamp = format_event_timestamp(event.timestamp)
    envelopes: list[dict[str, object]] = []
    parts = event.content.parts if event.content and event.content.parts else []

    for part_index, part in enumerate(parts):
        suffix = f"{event_id}-{part_index}"

        # 處理工具調用 (Tool Call)
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

        # 處理工具回傳結果 (Tool Result)
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

        # 處理文字內容 (Agent 回覆)
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
            # message 類型封包用於前端更新對話氣泡
            envelopes.append(
                {
                    "type": "message",
                    "text": text,
                    "mode": "append" if event.partial else "replace",
                    "final": not bool(event.partial),
                }
            )

    # 處理 session 狀態變更 (state_delta)
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
    """
    管理 Agent 執行週期的核心服務類別。
    """
    def __init__(
        self,
        runner: Runner,
        sessions: SessionService,
        config: AppRuntimeConfig,
    ) -> None:
        """
        初始化 AgentRunService。

        Args:
            runner: ADK Runner 實例。
            sessions: Session 服務實例。
            config: 應用程式配置。
        """
        self._runner = runner
        self._sessions = sessions
        self._config = config

    async def ensure_session(
        self,
        session_id: str,
        initial_state: dict[str, str] | None = None,
        user_id: str | None = None,
    ) -> None:
        """
        確保指定的對話視窗 (Session) 存在，若不存在則建立。
        """
        await self._sessions.ensure_session(session_id, initial_state, user_id=user_id)

    async def stream(
        self,
        *,
        prompt: str,
        session_id: str,
        session_state: dict[str, str] | None = None,
        user_id: str | None = None,
    ) -> AsyncGenerator[dict[str, object], None]:
        """
        執行 Agent 並串流回傳結果。

        此方法會封裝 ADK 事件為前端定義的通訊封包格式，並處理狀態合併。

        Args:
            prompt: 使用者輸入文字。
            session_id: 對話 ID。
            session_state: 本次執行的初始狀態補丁。
            user_id: 使用者 ID (選填)。

        Yields:
            各種類型的封包字典 (meta, timeline, message, state, done, error)。
        """
        sequence = 0
        current_text = ""
        merged_state = dict(session_state or {})
        resolved_user_id = (
            user_id.strip() if user_id and user_id.strip() else self._config.api_user_id
        )

        # 1. 發送中繼資訊封包
        yield build_meta_envelope()

        try:
            # 2. 開始與 ADK Runner 互動並處理事件
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
                # 轉換 ADK 事件為多個前端封包
                envelopes = map_adk_event_to_envelopes(event, sequence)
                # 更新本地維護的狀態
                merged_state = merge_state_patches(merged_state, envelopes)

                for envelope in envelopes:
                    if envelope.get("type") == "message":
                        text = str(envelope.get("text", ""))
                        if envelope.get("mode") == "append":
                            current_text += text
                        else:
                            current_text = text

                    yield envelope

            # 3. 執行結束後，獲取最終持久化狀態
            final_state = await self._sessions.get_state(
                session_id=session_id,
                fallback_state=merged_state,
                user_id=user_id,
            )
            # 4. 發送完成封包
            yield build_done_envelope(
                final_text=current_text
                or "ADK runtime 已完成執行，請查看右側 event history。",
                state=final_state,
            )
        except Exception as exc:
            # 錯誤處理
            yield build_error_envelope(str(exc))
