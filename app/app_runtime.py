from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AppRuntimeConfig:
    app_name: str
    toolbox_server_url: str
    session_db_uri: str
    memory_mode: str
    model_name: str


def load_runtime_config() -> AppRuntimeConfig:
    return AppRuntimeConfig(
        app_name=os.getenv("ADK_APP_NAME", "app"),
        toolbox_server_url=os.getenv("TOOLBOX_SERVER_URL", "http://127.0.0.1:5000"),
        session_db_uri=os.getenv(
            "ADK_SESSION_DB_URI",
            "sqlite+aiosqlite:///./db/adk_sessions.db",
        ),
        memory_mode=os.getenv("ADK_MEMORY_MODE", "in_memory"),
        model_name=os.getenv("MODEL_NAME", "gemini-3-flash-preview"),
    )
