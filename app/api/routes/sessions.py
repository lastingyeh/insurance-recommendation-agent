from __future__ import annotations

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from app.api.dependencies import get_container
from app.api.schemas import SessionCreateRequest
from app.services.session_service import SessionService

router = APIRouter(prefix="/api/agent/sessions", tags=["sessions"])


def _get_session_service(request: Request) -> SessionService:
    return get_container(request).sessions


@router.get("")
async def list_sessions(
    request: Request,
    user_id: str | None = Query(default=None, alias="userId"),
):
    try:
        sessions = await _get_session_service(request).list_sessions(user_id=user_id)
        return {"sessions": sessions}
    except Exception as exc:
        # セッション一覧が取得できない場合は空リストを返す（502 で UI を壊さない）
        import logging

        logging.getLogger(__name__).warning("list_sessions failed: %s", exc)
        return {"sessions": []}


@router.post("")
async def create_session(payload: SessionCreateRequest, request: Request):
    session_id = payload.sessionId.strip()
    if not session_id:
        return JSONResponse(
            status_code=400,
            content={"error": "sessionId is required"},
        )

    try:
        await _get_session_service(request).ensure_session(
            session_id, payload.state, user_id=payload.userId
        )
        return {"ok": True}
    except Exception as exc:
        return JSONResponse(
            status_code=502,
            content={"error": f"Failed to create session: {exc}"},
        )


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    request: Request,
    user_id: str | None = Query(default=None, alias="userId"),
):
    normalized_session_id = session_id.strip()
    if not normalized_session_id:
        return JSONResponse(
            status_code=400,
            content={"error": "sessionId is required"},
        )

    try:
        await _get_session_service(request).delete_session(
            normalized_session_id, user_id=user_id
        )
        return {"ok": True}
    except Exception as exc:
        return JSONResponse(
            status_code=502,
            content={"error": f"Failed to delete session: {exc}"},
        )
