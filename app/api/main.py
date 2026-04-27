from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.dependencies import get_container
from app.api.routes import run_router, session_router
from app.container import AppContainer, build_app_container


def create_app(container: AppContainer | None = None) -> FastAPI:
    app_container = container or build_app_container()
    config = app_container.config

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.container = app_container
        yield

    app = FastAPI(
        title="Insurance Recommendation Agent API",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(config.cors_allow_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/healthz")
    async def healthz():
        return {
            "status": "ok",
            "appName": config.app_name,
        }

    @app.get("/readyz")
    async def readyz(request: Request):
        container = get_container(request)
        errors = await container.readiness.collect_errors()

        if errors:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "not_ready",
                    "errors": errors,
                },
            )

        return {
            "status": "ok",
            "appName": container.config.app_name,
            "toolboxServerUrl": container.config.toolbox_server_url,
        }

    app.include_router(session_router)
    app.include_router(run_router)
    return app


app = create_app()
