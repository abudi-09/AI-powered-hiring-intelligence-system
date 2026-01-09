from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class InsightCreate(BaseModel):
    entity_type: str = Field(pattern="^(job|candidate)$")
    entity_id: uuid.UUID
    insight_type: str = Field(max_length=100)
    title: str = Field(max_length=255)
    description: str
    severity: str = Field(pattern="^(low|medium|high)$")
    confidence_score: float = Field(ge=0, le=100)
    data: dict | None = None


class InsightRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    insight_type: str
    title: str
    description: str
    severity: str
    confidence_score: float
    data: dict | None
    created_at: datetime


class InsightList(BaseModel):
    insights: list[InsightRead]
    total: int = 0
    
    def __init__(self, insights: list[InsightRead], **kwargs):
        super().__init__(insights=insights, total=len(insights), **kwargs)
