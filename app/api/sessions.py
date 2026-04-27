from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.api.dependencies import get_container
from app.api.schemas import SessionCreateRequest
from app.services.session_service import SessionService

router = APIRouter(prefix="/api/agent/sessions", tags=["sessions"])


def _get_session_service(request: Request) -> SessionService:
    return get_container(request).sessions


@router.get("")
async def list_sessions(request: Request):
    try:
        sessions = await _get_session_service(request).list_sessions()
        return {"sessions": sessions}
    except Exception as exc:
        return JSONResponse(
            status_code=502,
            content={"error": f"Unable to list sessions: {exc}"},
        )


@router.post("")
async def create_session(payload: SessionCreateRequest, request: Request):
    session_id = payload.sessionId.strip()
    if not session_id:
        return JSONResponse(
            status_code=400,
            content={"error": "sessionId is required"},
        )

    try:
        await _get_session_service(request).ensure_session(session_id, payload.state)
        return {"ok": True}
    except Exception as exc:
        return JSONResponse(
            status_code=502,
            content={"error": f"Failed to create session: {exc}"},
        )


@router.delete("/{session_id}")
async def delete_session(session_id: str, request: Request):
    normalized_session_id = session_id.strip()
    if not normalized_session_id:
        return JSONResponse(
            status_code=400,
            content={"error": "sessionId is required"},
        )

    try:
        await _get_session_service(request).delete_session(normalized_session_id)
        return {"ok": True}
    except Exception as exc:
        return JSONResponse(
            status_code=502,
            content={"error": f"Failed to delete session: {exc}"},
        )