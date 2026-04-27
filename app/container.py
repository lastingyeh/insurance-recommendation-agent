from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions.base_session_service import BaseSessionService
from google.adk.sessions.database_session_service import DatabaseSessionService
from google.adk.sessions.sqlite_session_service import SqliteSessionService

from app.agent import create_agent
from app.config import AppRuntimeConfig, load_runtime_config
from app.services.agent_run_service import AgentRunService
from app.services.readiness_service import ReadinessService
from app.services.session_service import SessionService


def _normalize_sqlite_db_path(session_db_uri: str) -> str:
    parsed = urlparse(session_db_uri)
    db_path = parsed.path

    if db_path.startswith("/"):
        db_path = db_path[1:]

    return db_path or ":memory:"


def _is_sqlite_session_uri(session_db_uri: str) -> bool:
    parsed = urlparse(session_db_uri)
    return parsed.scheme.split("+", 1)[0] == "sqlite"


def create_session_store(config: AppRuntimeConfig) -> BaseSessionService:
    if _is_sqlite_session_uri(config.session_db_uri):
        return SqliteSessionService(
            db_path=_normalize_sqlite_db_path(config.session_db_uri)
        )

    return DatabaseSessionService(db_url=config.session_db_uri)


def create_runner(
    config: AppRuntimeConfig,
    agent: Agent,
    session_store: BaseSessionService,
) -> Runner:
    return Runner(
        app_name=config.app_name,
        agent=agent,
        session_service=session_store,
    )


@dataclass(frozen=True)
class AppContainer:
    config: AppRuntimeConfig
    agent: Agent
    session_store: BaseSessionService
    runner: Runner
    sessions: SessionService
    agent_runs: AgentRunService
    readiness: ReadinessService


def build_app_container(config: AppRuntimeConfig | None = None) -> AppContainer:
    runtime_config = config or load_runtime_config()
    agent = create_agent(runtime_config)
    session_store = create_session_store(runtime_config)
    runner = create_runner(runtime_config, agent, session_store)
    sessions = SessionService(session_store, runtime_config)
    return AppContainer(
        config=runtime_config,
        agent=agent,
        session_store=session_store,
        runner=runner,
        sessions=sessions,
        agent_runs=AgentRunService(runner, sessions, runtime_config),
        readiness=ReadinessService(session_store, runtime_config),
    )
