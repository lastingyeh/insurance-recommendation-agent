from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.api.dependencies import get_container
from app.api.schemas import SessionCreateRequest
from app.services.session_service import SessionService

router = APIRouter(tags=["sessions"])

_logger = logging.getLogger(__name__)


def _get_session_service(request: Request) -> SessionService:
    """
    從相依性注入容器中獲取 Session 管理服務。
    """
    return get_container(request).sessions


def _check_app_name(app_name: str, request: Request) -> bool:
    """
    驗證請求中的應用名稱是否與配置相符。
    """
    return app_name == get_container(request).config.app_name


# ─── 列出會話 ────────────────────────────────────────────────────────────


@router.get("/apps/{app_name}/users/{user_id}/sessions")
async def list_sessions(app_name: str, user_id: str, request: Request):
    """
    列出特定使用者在特定應用下的所有對話會話。
    """
    if not _check_app_name(app_name, request):
        return JSONResponse(status_code=404, content={"error": "app not found"})
    try:
        sessions = await _get_session_service(request).list_sessions(user_id=user_id)
        return {"sessions": sessions}
    except Exception as exc:
        _logger.warning("list_sessions failed: %s", exc)
        return {"sessions": []}


# ─── 建立會話 ───────────────────────────────────────────────────────────


@router.post("/apps/{app_name}/users/{user_id}/sessions")
async def create_session(
    app_name: str,
    user_id: str,
    payload: SessionCreateRequest,
    request: Request,
):
    """
    為特定使用者建立新的對話會話。
    如果未提供 sessionId，則會自動生成一個 UUID。
    """
    if not _check_app_name(app_name, request):
        return JSONResponse(status_code=404, content={"error": "app not found"})

    session_id = (payload.sessionId or "").strip() or str(uuid.uuid4())

    try:
        # 確保會話存在於儲存中，並可選地初始化狀態
        await _get_session_service(request).ensure_session(
            session_id, payload.state, user_id=user_id
        )
        return {"ok": True, "sessionId": session_id}
    except Exception as exc:
        return JSONResponse(
            status_code=502,
            content={"error": f"Failed to create session: {exc}"},
        )


# ─── 獲取會話詳情 ──────────────────────────────────────────────────────────────


@router.get("/apps/{app_name}/users/{user_id}/sessions/{session_id}")
async def get_session(
    app_name: str,
    user_id: str,
    session_id: str,
    request: Request,
):
    """
    獲取指定會話的詳細資訊。
    """
    if not _check_app_name(app_name, request):
        return JSONResponse(status_code=404, content={"error": "app not found"})

    session_data = await _get_session_service(request).get_session(
        session_id, user_id=user_id
    )
    if session_data is None:
        return JSONResponse(status_code=404, content={"error": "session not found"})
    return session_data


# ─── 刪除會話 ───────────────────────────────────────────────────────────


@router.delete("/apps/{app_name}/users/{user_id}/sessions/{session_id}")
async def delete_session(
    app_name: str,
    user_id: str,
    session_id: str,
    request: Request,
):
    """
    刪除指定的對話會話。
    """
    if not _check_app_name(app_name, request):
        return JSONResponse(status_code=404, content={"error": "app not found"})

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
