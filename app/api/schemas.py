from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AgentRunRequest(BaseModel):
    """
    代理程式執行請求的資料模型 (Data Model)。

    用於接收客戶端發送給 AI 代理程式的執行請求參數。
    """

    prompt: str = Field(
        min_length=1, description="使用者的輸入提示或對話內容，不可為空"
    )
    sessionId: str = Field(
        min_length=1, description="工作階段的唯一識別碼，用於追蹤上下文對話，不可為空"
    )
    userId: str | None = Field(
        default=None, description="使用者的唯一識別碼，為可選填位"
    )
    sessionState: dict[str, str] = Field(
        default_factory=dict, description="工作階段的狀態字典，用於傳遞上下文狀態參數"
    )


class SessionCreateRequest(BaseModel):
    """
    建立新工作階段請求的資料模型。

    用於接收初始化或建立新對話工作階段時的參數。
    """

    sessionId: str | None = Field(
        default=None, description="指定的工作階段識別碼，若未提供則由系統自動生成"
    )
    state: dict[str, Any] = Field(
        default_factory=dict, description="初始化時要設定的工作階段狀態"
    )
