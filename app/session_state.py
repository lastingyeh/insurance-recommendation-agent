from __future__ import annotations

USER_PROFILE_STATE_KEYS: tuple[str, ...] = (
    "user:age",
    "user:budget",
    "user:main_goal",
    "user:marital_status",
    "user:has_children",
    "user:existing_coverage",
    "user:risk_preference",
)

LAST_RECOMMENDATION_STATE_KEYS: tuple[str, ...] = (
    "user:last_recommended_product_name",
    "user:last_recommended_product_id",
)

TRACKED_PROFILE_STATE_KEYS: tuple[str, ...] = (
    *USER_PROFILE_STATE_KEYS,
    *LAST_RECOMMENDATION_STATE_KEYS,
)

UI_STATE_PREFIX = "_ui_"


def is_ui_state_key(key: str) -> bool:
    return key.startswith(UI_STATE_PREFIX)