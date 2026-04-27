from __future__ import annotations

from typing import Any

from google.adk.tools.tool_context import ToolContext

from app.session_state import (
    LAST_RECOMMENDATION_STATE_KEYS,
    TRACKED_PROFILE_STATE_KEYS,
)


def get_user_profile_snapshot(tool_context: ToolContext) -> dict[str, Any]:
    """
    Read the current session/user profile snapshot from ADK state.

    Returns only the keys relevant to insurance recommendation.
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
    Persist user profile fields into ADK state.

    Only provided fields are updated.
    """
    if tool_context is None:
        raise ValueError("tool_context is required")

    updated: dict[str, Any] = {}

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
    Persist the last recommended product into ADK state.
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
    Remove the last recommendation pointer from ADK state.
    """
    for key in LAST_RECOMMENDATION_STATE_KEYS:
        if key in tool_context.state:
            del tool_context.state[key]

    return {"status": "ok"}
