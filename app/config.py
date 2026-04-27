from __future__ import annotations

import os
from dataclasses import dataclass


def _parse_bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_csv_env(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    value = os.getenv(name)
    if value is None:
        return default

    items = tuple(item.strip() for item in value.split(",") if item.strip())
    return items or default


@dataclass(frozen=True)
class AppRuntimeConfig:
    app_name: str
    api_user_id: str
    toolbox_server_url: str
    session_db_uri: str
    memory_mode: str
    model_name: str
    fastapi_host: str
    fastapi_port: int
    fastapi_reload: bool
    cors_allow_origins: tuple[str, ...]


def load_runtime_config() -> AppRuntimeConfig:
    return AppRuntimeConfig(
        app_name=os.getenv("ADK_APP_NAME", "app"),
        api_user_id=os.getenv("ADK_API_USER_ID", "demo-user"),
        toolbox_server_url=os.getenv("TOOLBOX_SERVER_URL", "http://127.0.0.1:5000"),
        session_db_uri=os.getenv(
            "ADK_SESSION_DB_URI",
            "sqlite+aiosqlite:///./db/adk_sessions.db",
        ),
        memory_mode=os.getenv("ADK_MEMORY_MODE", "in_memory"),
        model_name=os.getenv("MODEL_NAME", "gemini-3-flash-preview"),
        fastapi_host=os.getenv("FASTAPI_HOST", "127.0.0.1"),
        fastapi_port=int(os.getenv("FASTAPI_PORT", "8080")),
        fastapi_reload=_parse_bool_env("FASTAPI_RELOAD", True),
        cors_allow_origins=_parse_csv_env(
            "FASTAPI_CORS_ALLOW_ORIGINS",
            ("http://127.0.0.1:3000", "http://localhost:3000"),
        ),
    )


__all__ = ["AppRuntimeConfig", "load_runtime_config"]
