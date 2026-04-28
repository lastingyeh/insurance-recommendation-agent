"""
Session 管理服務模組。
負責管理使用者對話視窗 (Session) 的生命週期，包括建立、讀取、列出、刪除以及狀態同步。
"""

from __future__ import annotations

import json
import time
from typing import Any

from google.adk.sessions.base_session_service import BaseSessionService
from google.adk.sessions.session import Session

from app.config import AppRuntimeConfig
from app.session_state import is_ui_state_key


def safe_stringify(value: Any) -> str:
    """
    安全地將任意值轉換為字串格式。

    對於基本類型直接轉換，對於複雜類型 (如 dict, list) 嘗試序列化為 JSON，失敗則回傳 str(value)。
    """
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
    """
    建立對外公開的狀態字典。

    過濾掉內部使用的 UI 狀態鍵（以底線開頭的鍵），並將其餘值轉換為字串。
    """
    return {
        key: safe_stringify(value)
        for key, value in raw_state.items()
        if not is_ui_state_key(key)
    }


def format_updated_at(last_update_time: float) -> str:
    """
    將上次更新的時間戳記格式化為易讀的相對時間字串。

    例如：「剛剛」、「5 分鐘前」、「2 小時前」等。
    """
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
    """
    將 ADK Session 物件轉換為前端列表所需的字典格式。
    """
    raw_state = dict(session.state)
    # 嘗試從狀態中提取自定義的標題與副標題
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
        "_updateTime": session.last_update_time, # 用於排序
    }


class SessionService:
    """
    提供 Session 相關操作的核心服務類別。
    """
    def __init__(
        self,
        session_store: BaseSessionService,
        config: AppRuntimeConfig,
    ) -> None:
        """
        初始化 SessionService。
        """
        self._session_store = session_store
        self._config = config

    def _resolve_user_id(self, user_id: str | None) -> str:
        """
        解析使用者 ID，若未提供則回傳配置中的預設 ID。
        """
        if user_id and user_id.strip():
            return user_id.strip()
        return self._config.api_user_id

    async def list_sessions(self, user_id: str | None = None) -> list[dict[str, Any]]:
        """
        列出指定使用者的所有對話 Session，並依更新時間降序排序。
        """
        response = await self._session_store.list_sessions(
            app_name=self._config.app_name,
            user_id=self._resolve_user_id(user_id),
        )

        sessions = [to_session_list_item(session) for session in response.sessions]
        # 依更新時間排序 (最新優先)
        sessions.sort(key=lambda item: item["_updateTime"], reverse=True)

        # 移除僅供內部排序使用的 _updateTime 鍵
        return [
            {key: value for key, value in session.items() if key != "_updateTime"}
            for session in sessions
        ]

    async def get_session(
        self,
        session_id: str,
        user_id: str | None = None,
    ) -> dict[str, Any] | None:
        """
        獲取特定對話 Session 的詳細資訊。
        """
        resolved_user_id = self._resolve_user_id(user_id)
        session = await self._session_store.get_session(
            app_name=self._config.app_name,
            user_id=resolved_user_id,
            session_id=session_id,
        )
        if session is None:
            return None
        return to_session_list_item(session)

    async def ensure_session(
        self,
        session_id: str,
        initial_state: dict[str, Any] | None = None,
        user_id: str | None = None,
    ) -> Session:
        """
        確保 Session 存在，若不存在則建立。
        """
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
        """
        刪除指定的 Session。
        """
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
        """
        獲取 Session 的狀態，並可選擇與提供的備用狀態合併。

        Args:
            session_id: Session ID。
            fallback_state: 備用狀態字典，通常是記憶體中最新的狀態補丁。
            user_id: 使用者 ID。

        Returns:
            合併後的狀態字典。
        """
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

        # 合併持久化狀態與備用/記憶體狀態 (備用狀態優先更新)
        return {
            **persisted_state,
            **fallback_state,
        }


# --- 以下為便利函式 (Helper Functions)，用於直接調用服務 ---

async def list_sessions_for_ui(
    session_store: BaseSessionService,
    config: AppRuntimeConfig,
) -> list[dict[str, Any]]:
    """列出 UI 顯示用的 Session 列表"""
    return await SessionService(session_store, config).list_sessions()


async def create_session_if_missing(
    session_store: BaseSessionService,
    config: AppRuntimeConfig,
    session_id: str,
    initial_state: dict[str, Any] | None = None,
) -> Session:
    """如果 Session 不存在則建立"""
    return await SessionService(session_store, config).ensure_session(
        session_id,
        initial_state,
    )


async def delete_session_if_exists(
    session_store: BaseSessionService,
    config: AppRuntimeConfig,
    session_id: str,
) -> None:
    """如果 Session 存在則刪除"""
    await SessionService(session_store, config).delete_session(session_id)


async def get_session_state(
    session_store: BaseSessionService,
    config: AppRuntimeConfig,
    session_id: str,
    fallback_state: dict[str, str] | None = None,
) -> dict[str, str]:
    """獲取 Session 狀態"""
    return await SessionService(session_store, config).get_state(
        session_id,
        fallback_state,
    )
