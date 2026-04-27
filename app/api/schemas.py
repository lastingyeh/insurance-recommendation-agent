from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AgentRunRequest(BaseModel):
    prompt: str = Field(min_length=1)
    sessionId: str = Field(min_length=1)
    userId: str | None = Field(default=None)
    sessionState: dict[str, str] = Field(default_factory=dict)


class SessionCreateRequest(BaseModel):
    sessionId: str = Field(min_length=1)
    userId: str | None = Field(default=None)
    state: dict[str, Any] = Field(default_factory=dict)
