from __future__ import annotations

# 定義與使用者個人資料相關的 Session 狀態鍵名
# 代理人會使用這些鍵名在 Session 中儲存或讀取使用者的特徵資訊
USER_PROFILE_STATE_KEYS: tuple[str, ...] = (
    "user:age",                 # 年齡
    "user:budget",              # 預算
    "user:main_goal",           # 主要保險目標
    "user:marital_status",      # 婚姻狀況
    "user:has_children",        # 是否有子女
    "user:existing_coverage",   # 現有保障情況
    "user:risk_preference",     # 風險偏好
)

# 定義與最後一次推薦結果相關的 Session 狀態鍵名
LAST_RECOMMENDATION_STATE_KEYS: tuple[str, ...] = (
    "user:last_recommended_product_name", # 最後推薦的產品名稱
    "user:last_recommended_product_id",   # 最後推薦的產品 ID
)

# 合併所有需要追踪的使用者個人資料狀態鍵名
TRACKED_PROFILE_STATE_KEYS: tuple[str, ...] = (
    *USER_PROFILE_STATE_KEYS,
    *LAST_RECOMMENDATION_STATE_KEYS,
)

# 前端 UI 專用的狀態前綴，用於區分業務邏輯狀態與介面展示狀態
UI_STATE_PREFIX = "_ui_"


def is_ui_state_key(key: str) -> bool:
    """
    判斷給定的鍵名是否為前端 UI 專用的狀態。
    """
    return key.startswith(UI_STATE_PREFIX)
