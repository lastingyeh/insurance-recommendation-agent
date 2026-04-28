from __future__ import annotations

from typing import Any

from google.adk.tools.tool_context import ToolContext

from app.session_state import (
    LAST_RECOMMENDATION_STATE_KEYS,
    TRACKED_PROFILE_STATE_KEYS,
)

"""
本模組定義了與會話狀態（Session State）相關的工具函式，
主要用於管理用戶畫像（User Profile）及推薦紀錄。
這些工具讓 AI 代理人（Agent）能夠在對話過程中存取與持久化用戶資訊。
"""


def get_user_profile_snapshot(tool_context: ToolContext) -> dict[str, Any]:
    """
    從 ADK 狀態中讀取當前會話/用戶畫像的快照。

    此函式會過濾並僅返回與保險推薦相關的鍵值對。

    參數:
        tool_context: ADK 工具上下文，包含當前的會話狀態。

    返回:
        包含用戶畫像資訊的字典（例如：年齡、預算、目標等）。
    """
    snapshot: dict[str, Any] = {}
    for key in TRACKED_PROFILE_STATE_KEYS:
        value = tool_context.state.get(key)
        if value is not None:
            snapshot[key] = value

    return snapshot


def save_user_profile(
    age: int | None = None,
    budget: int | None = None,
    main_goal: str | None = None,
    marital_status: str | None = None,
    has_children: bool | None = None,
    existing_coverage: str | None = None,
    risk_preference: str | None = None,
    tool_context: ToolContext | None = None,
) -> dict[str, Any]:
    """
    將用戶畫像欄位持久化至 ADK 狀態中。

    僅會更新有提供的欄位（非 None 的值）。

    參數:
        age: 用戶年齡。
        budget: 用戶預算。
        main_goal: 主要保險目標（例如：醫療、意外、理財）。
        marital_status: 婚姻狀況。
        has_children: 是否有小孩。
        existing_coverage: 現有的保險覆蓋狀況。
        risk_preference: 風險偏好（例如：保守、積極）。
        tool_context: ADK 工具上下文（必填）。

    異常:
        ValueError: 當未提供 tool_context 時拋出。

    返回:
        包含處理狀態及已更新欄位的字典。
    """
    if tool_context is None:
        raise ValueError("tool_context is required")

    updated: dict[str, Any] = {}

    # 建立映射表並進行基本的格式化（去空白與小寫化）
    mapping = {
        "user:age": age,
        "user:budget": budget,
        "user:main_goal": (
            main_goal.strip().lower() if isinstance(main_goal, str) else None
        ),
        "user:marital_status": (
            marital_status.strip().lower() if isinstance(marital_status, str) else None
        ),
        "user:has_children": has_children,
        "user:existing_coverage": (
            existing_coverage.strip().lower()
            if isinstance(existing_coverage, str)
            else None
        ),
        "user:risk_preference": (
            risk_preference.strip().lower()
            if isinstance(risk_preference, str)
            else None
        ),
    }

    # 更新狀態字典
    for key, value in mapping.items():
        if value is not None:
            tool_context.state[key] = value
            updated[key] = value

    return {
        "status": "ok",
        "updated": updated,
    }


def save_last_recommendation(
    product_name: str,
    product_id: int | None = None,
    tool_context: ToolContext | None = None,
) -> dict[str, Any]:
    """
    將最後一次推薦的產品資訊持久化至 ADK 狀態中。

    這有助於 Agent 在後續對話中追蹤推薦脈絡，例如用戶詢問「關於剛才那個產品...」。

    參數:
        product_name: 推薦的產品名稱。
        product_id: 推薦的產品 ID（選填）。
        tool_context: ADK 工具上下文（必填）。

    異常:
        ValueError: 當未提供 tool_context 時拋出。

    返回:
        包含處理狀態及產品資訊的字典。
    """
    if tool_context is None:
        raise ValueError("tool_context is required")

    tool_context.state["user:last_recommended_product_name"] = product_name
    if product_id is not None:
        tool_context.state["user:last_recommended_product_id"] = product_id

    return {
        "status": "ok",
        "product_name": product_name,
        "product_id": product_id,
    }


def clear_last_recommendation(tool_context: ToolContext) -> dict[str, str]:
    """
    從 ADK 狀態中移除最後一次推薦的紀錄。

    常用於重置對話狀態或開始新的推薦流程。

    參數:
        tool_context: ADK 工具上下文。

    返回:
        處理狀態字典。
    """
    for key in LAST_RECOMMENDATION_STATE_KEYS:
        if key in tool_context.state:
            del tool_context.state[key]

    return {"status": "ok"}
