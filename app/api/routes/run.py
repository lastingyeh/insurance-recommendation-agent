from __future__ import annotations

import json
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

from app.api.dependencies import get_container
from app.api.schemas import AgentRunRequest
from app.services.agent_run_service import AgentRunService


def encode_sse_event(envelope: dict[str, object]) -> str:
    """
    將資料封裝為伺服器傳送事件 (SSE) 格式。
    """
    return f"data: {json.dumps(envelope, ensure_ascii=False)}\n\n"


router = APIRouter(prefix="/api/agent", tags=["agent"])


def get_runner(request: Request | None = None):
    """
    從相依性注入容器中獲取 Runner 實例。
    """
    return get_container(request).runner


def get_agent_run_service(request: Request) -> AgentRunService:
    """
    獲取 Agent 執行服務。如果 Runner 不同於容器預設，則建立新的服務實例。
    """
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
    """
    執行 Agent 的主要 API 端點。
    接收使用者提示詞，並以流式 (Streaming) 方式回傳回應。
    """
    prompt = payload.prompt.strip()
    session_id = payload.sessionId.strip()

    # 驗證必要欄位
    if not prompt or not session_id:
        return JSONResponse(
            status_code=400,
            content={"error": "prompt and sessionId are required"},
        )

    run_service = get_agent_run_service(request)

    try:
        # 確保對話會話存在並同步狀態
        await run_service.ensure_session(
            session_id, payload.sessionState, user_id=payload.userId
        )
    except Exception as exc:
        return JSONResponse(
            status_code=502,
            content={"error": f"Unable to ensure session: {exc}"},
        )

    async def sse_generator() -> AsyncGenerator[str, None]:
        """
        生成 SSE 格式的流式輸出。
        """
        async for envelope in run_service.stream(
            prompt=prompt,
            session_id=session_id,
            session_state=payload.sessionState,
            user_id=payload.userId,
        ):
            yield encode_sse_event(envelope)

    # 回傳流式回應，設定正確的媒體類型與標頭以支援 SSE
    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
        },
    )
