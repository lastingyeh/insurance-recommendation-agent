from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.dependencies import get_container
from app.api.routes import run_router, session_router
from app.container import AppContainer, build_app_container


def create_app(container: AppContainer | None = None) -> FastAPI:
    # 初始化應用程式容器，使用提供的容器或建立新的容器
    app_container = container or build_app_container()
    # 從容器中獲取配置物件
    config = app_container.config

    # 定義應用程式生命週期上下文管理器，用於處理啟動和關閉事件
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # 在啟動期間將容器儲存在應用程式狀態中
        app.state.container = app_container
        # yield 語句允許應用程式正常執行
        yield

    # 建立 FastAPI 應用程式實例
    app = FastAPI(
        title="Insurance Recommendation Agent API",
        version="0.1.0",
        lifespan=lifespan,
    )
    # 配置 CORS 中介軟體，設定從配置中允許的來源
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(config.cors_allow_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 健康檢查端點：用於驗證應用程式基本狀態是否正常
    @app.get("/healthz")
    async def healthz():
        # 返回包含應用程式狀態和名稱的健康檢查結果
        return {
            "status": "ok",
            "appName": config.app_name,
        }

    # 就緒檢查端點：驗證所有依賴項是否都正常運作
    @app.get("/readyz")
    async def readyz(request: Request):
        # 從請求狀態中獲取容器物件
        container = get_container(request)
        # 蒐集任何就緒檢查中發現的錯誤
        errors = await container.readiness.collect_errors()

        # 如果檢測到錯誤，返回服務不可用狀態碼 503
        if errors:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "not_ready",
                    "errors": errors,
                },
            )

        # 如果一切正常，返回就緒狀態及配置詳細資訊
        return {
            "status": "ok",
            "appName": container.config.app_name,
            "toolboxServerUrl": container.config.toolbox_server_url,
        }

    # 包含應用程式路由器，將會話路由和執行路由整合到應用程式中
    app.include_router(session_router)
    app.include_router(run_router)
    # 返回配置完整的 FastAPI 應用程式實例
    return app


# 建立並初始化應用程式的全域實例
app = create_app()
