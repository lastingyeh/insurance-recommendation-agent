"""
系統就緒檢測服務模組。
負責檢查應用程式相依的外部服務（如 Session Store、Toolbox Server）是否正常運作。
"""

from __future__ import annotations

import asyncio

import requests

from google.adk.sessions.base_session_service import BaseSessionService

from app.config import AppRuntimeConfig


class ReadinessService:
    """
    提供系統健康狀況檢查功能的服務類別。
    """
    def __init__(
        self,
        session_store: BaseSessionService,
        config: AppRuntimeConfig,
    ) -> None:
        """
        初始化 ReadinessService。

        Args:
            session_store: ADK Session 存儲服務實例。
            config: 應用程式配置。
        """
        self._session_store = session_store
        self._config = config

    async def collect_errors(self) -> list[str]:
        """
        收集系統中可能的錯誤或連線問題。

        檢查項目包括：
        1. Session Store 是否正常初始化。
        2. Toolbox Server (工具箱伺服器) 是否可連通。

        Returns:
            包含錯誤描述字串的列表。若列表為空，代表系統就緒狀況良好。
        """
        errors: list[str] = []

        # 1. 檢查 Session Store 存取狀況
        try:
            # 嘗試存取屬性，確認對象已正確注入
            self._session_store
        except Exception as exc:
            errors.append(f"session_service: {exc}")

        # 2. 檢查 Toolbox Server 連線狀況
        try:
            # 使用 asyncio.to_thread 以非同步方式執行同步的 requests 調用
            await asyncio.to_thread(
                requests.get,
                self._config.toolbox_server_url,
                timeout=1,
            )
        except requests.RequestException as exc:
            errors.append(f"toolbox: {exc}")

        return errors
