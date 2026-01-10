from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ChatQueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    session_id: uuid.UUID | None = None


class ChatMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: str
    content: str
    intent: str | None
    entities: dict | None
    confidence: float | None
    sources: list[str] | None
    created_at: datetime


class ChatQueryResponse(BaseModel):
    session_id: uuid.UUID
    message: str
    bullets: list[str]
    confidence: float
    sources: list[str]
    intent: str
    entities: dict


class ConversationSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    title: str | None
    context: dict | None
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


class ConversationSessionDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    title: str | None
    context: dict | None
    created_at: datetime
    updated_at: datetime
    messages: list[ChatMessageRead]
