from __future__ import annotations

import asyncio

import requests

from google.adk.sessions.base_session_service import BaseSessionService

from app.config import AppRuntimeConfig


class ReadinessService:
    def __init__(
        self,
        session_store: BaseSessionService,
        config: AppRuntimeConfig,
    ) -> None:
        self._session_store = session_store
        self._config = config

    async def collect_errors(self) -> list[str]:
        errors: list[str] = []

        try:
            self._session_store
        except Exception as exc:
            errors.append(f"session_service: {exc}")

        try:
            await asyncio.to_thread(
                requests.get,
                self._config.toolbox_server_url,
                timeout=1,
            )
        except requests.RequestException as exc:
            errors.append(f"toolbox: {exc}")

        return errors
