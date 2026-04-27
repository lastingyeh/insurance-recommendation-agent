from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

from app.api.dependencies import get_container
from app.api.schemas import AgentRunRequest
from app.api.sse import encode_sse_event
from app.services.agent_run_service import AgentRunService

router = APIRouter(prefix="/api/agent", tags=["agent"])


def get_runner(request: Request | None = None):
    return get_container(request).runner


def get_agent_run_service(request: Request) -> AgentRunService:
    container = get_container(request)

    try:
        runner = get_runner(request)
    except TypeError:
        runner = get_runner()

    if runner is container.runner:
        return container.agent_runs

    return AgentRunService(runner, container.sessions, container.config)


@router.post("/run")
async def run_agent(payload: AgentRunRequest, request: Request):
    prompt = payload.prompt.strip()
    session_id = payload.sessionId.strip()

    if not prompt or not session_id:
        return JSONResponse(
            status_code=400,
            content={"error": "prompt and sessionId are required"},
        )

    run_service = get_agent_run_service(request)

    try:
        await run_service.ensure_session(
            session_id, payload.sessionState, user_id=payload.userId
        )
    except Exception as exc:
        return JSONResponse(
            status_code=502,
            content={"error": f"Unable to ensure session: {exc}"},
        )

    async def sse_generator() -> AsyncGenerator[str, None]:
        async for envelope in run_service.stream(
            prompt=prompt,
            session_id=session_id,
            session_state=payload.sessionState,
            user_id=payload.userId,
        ):
            yield encode_sse_event(envelope)

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
        },
    )
