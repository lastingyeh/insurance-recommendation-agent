from __future__ import annotations

import json
import time
from typing import Any

from google.adk.sessions.base_session_service import BaseSessionService
from google.adk.sessions.session import Session

from app.config import AppRuntimeConfig
from app.session_state import is_ui_state_key


def safe_stringify(value: Any) -> str:
    if isinstance(value, str):
        return value

    if value is None:
        return "None"

    try:
        return (
            str(value) if isinstance(value, (int, float, bool)) else json.dumps(value)
        )
    except Exception:
        return str(value)


def build_public_state(raw_state: dict[str, Any]) -> dict[str, str]:
    return {
        key: safe_stringify(value)
        for key, value in raw_state.items()
        if not is_ui_state_key(key)
    }


def format_updated_at(last_update_time: float) -> str:
    if not last_update_time:
        return "已儲存"

    diff_seconds = max(0, int(time.time() - last_update_time))
    minutes = diff_seconds // 60

    if minutes < 1:
        return "剛剛"
    if minutes < 60:
        return f"{minutes} 分鐘前"

    hours = minutes // 60
    if hours < 24:
        return f"{hours} 小時前"

    return f"{hours // 24} 天前"


def to_session_list_item(session: Session) -> dict[str, Any]:
    raw_state = dict(session.state)
    ui_title = raw_state.get("_ui_title")
    ui_subtitle = raw_state.get("_ui_subtitle")

    title = ui_title if isinstance(ui_title, str) and ui_title.strip() else None
    subtitle = (
        ui_subtitle if isinstance(ui_subtitle, str) and ui_subtitle.strip() else None
    )

    return {
        "id": session.id,
        "title": title or f"對話 {session.id[-6:]}",
        "subtitle": subtitle or "繼續上次的對話",
        "status": "idle",
        "updatedAt": format_updated_at(session.last_update_time),
        "messages": [],
        "events": [],
        "state": build_public_state(raw_state),
        "_updateTime": session.last_update_time,
    }


class SessionService:
    def __init__(
        self,
        session_store: BaseSessionService,
        config: AppRuntimeConfig,
    ) -> None:
        self._session_store = session_store
        self._config = config

    def _resolve_user_id(self, user_id: str | None) -> str:
        if user_id and user_id.strip():
            return user_id.strip()
        return self._config.api_user_id

    async def list_sessions(self, user_id: str | None = None) -> list[dict[str, Any]]:
        response = await self._session_store.list_sessions(
            app_name=self._config.app_name,
            user_id=self._resolve_user_id(user_id),
        )

        sessions = [to_session_list_item(session) for session in response.sessions]
        sessions.sort(key=lambda item: item["_updateTime"], reverse=True)

        return [
            {key: value for key, value in session.items() if key != "_updateTime"}
            for session in sessions
        ]

    async def ensure_session(
        self,
        session_id: str,
        initial_state: dict[str, Any] | None = None,
        user_id: str | None = None,
    ) -> Session:
        resolved_user_id = self._resolve_user_id(user_id)
        existing = await self._session_store.get_session(
            app_name=self._config.app_name,
            user_id=resolved_user_id,
            session_id=session_id,
        )
        if existing is not None:
            return existing

        return await self._session_store.create_session(
            app_name=self._config.app_name,
            user_id=resolved_user_id,
            session_id=session_id,
            state=initial_state or {},
        )

    async def delete_session(self, session_id: str, user_id: str | None = None) -> None:
        resolved_user_id = self._resolve_user_id(user_id)
        existing = await self._session_store.get_session(
            app_name=self._config.app_name,
            user_id=resolved_user_id,
            session_id=session_id,
        )
        if existing is None:
            return

        await self._session_store.delete_session(
            app_name=self._config.app_name,
            user_id=resolved_user_id,
            session_id=session_id,
        )

    async def get_state(
        self,
        session_id: str,
        fallback_state: dict[str, str] | None = None,
        user_id: str | None = None,
    ) -> dict[str, str]:
        resolved_user_id = self._resolve_user_id(user_id)
        session = await self._session_store.get_session(
            app_name=self._config.app_name,
            user_id=resolved_user_id,
            session_id=session_id,
        )

        if session is None:
            return fallback_state or {}

        persisted_state = build_public_state(dict(session.state))

        if not fallback_state:
            return persisted_state

        return {
            **persisted_state,
            **fallback_state,
        }


async def list_sessions_for_ui(
    session_store: BaseSessionService,
    config: AppRuntimeConfig,
) -> list[dict[str, Any]]:
    return await SessionService(session_store, config).list_sessions()


async def create_session_if_missing(
    session_store: BaseSessionService,
    config: AppRuntimeConfig,
    session_id: str,
    initial_state: dict[str, Any] | None = None,
) -> Session:
    return await SessionService(session_store, config).ensure_session(
        session_id,
        initial_state,
    )


async def delete_session_if_exists(
    session_store: BaseSessionService,
    config: AppRuntimeConfig,
    session_id: str,
) -> None:
    await SessionService(session_store, config).delete_session(session_id)


async def get_session_state(
    session_store: BaseSessionService,
    config: AppRuntimeConfig,
    session_id: str,
    fallback_state: dict[str, str] | None = None,
) -> dict[str, str]:
    return await SessionService(session_store, config).get_state(
        session_id,
        fallback_state,
    )
