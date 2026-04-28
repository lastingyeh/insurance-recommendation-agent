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
    """
    從資料庫連線字串中提取 SQLite 檔案路徑。
    例如：'sqlite:///./db/adk_sessions.db' -> './db/adk_sessions.db'
    """
    parsed = urlparse(session_db_uri)
    db_path = parsed.path

    if db_path.startswith("/"):
        db_path = db_path[1:]

    return db_path or ":memory:"


def _is_sqlite_session_uri(session_db_uri: str) -> bool:
    """
    檢查連線字串是否指定為 SQLite 資料庫。
    """
    parsed = urlparse(session_db_uri)
    return parsed.scheme.split("+", 1)[0] == "sqlite"


def create_session_store(config: AppRuntimeConfig) -> BaseSessionService:
    """
    根據配置建立對應的 Session 儲存服務實例。
    支援 SqliteSessionService 或泛用的 DatabaseSessionService。
    """
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
    """
    建立 Google ADK Runner 實例，負責協調代理人與對話 Session 的執行。
    """
    return Runner(
        app_name=config.app_name,
        agent=agent,
        session_service=session_store,
    )


@dataclass(frozen=True)
class AppContainer:
    """
    應用程式依賴注入容器。
    集中管理並持有應用程式運作所需的所有核心實例。
    """
    config: AppRuntimeConfig             # 配置
    agent: Agent                         # 代理人
    session_store: BaseSessionService     # Session 儲存
    runner: Runner                       # 執行器
    sessions: SessionService             # Session 管理服務
    agent_runs: AgentRunService          # 代理人執行任務服務
    readiness: ReadinessService          # 系統健康狀態服務


def build_app_container(config: AppRuntimeConfig | None = None) -> AppContainer:
    """
    建構並初始化 AppContainer。
    此函式負責組裝所有服務與元件的依賴關係。
    """
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
        # AgentRunService 負責封裝 Runner 的執行邏輯
        agent_runs=AgentRunService(runner, sessions, runtime_config),
        # ReadinessService 負責檢查系統相依性（如資料庫）是否正常
        readiness=ReadinessService(session_store, runtime_config),
    )
