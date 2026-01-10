from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RecommendationCreate(BaseModel):
    entity_type: str = Field(pattern="^(job|candidate)$")
    entity_id: uuid.UUID
    recommended_entity_id: uuid.UUID
    recommendation_type: str = Field(max_length=100)
    rank: int = Field(ge=1)
    score: float = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=100)
    explanation: dict


class RecommendationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    recommended_entity_id: uuid.UUID
    recommendation_type: str
    rank: int
    score: float
    confidence: float
    explanation: dict
    created_at: datetime


class RecommendationList(BaseModel):
    recommendations: list[RecommendationRead]
    total: int = 0

    def __init__(self, recommendations: list[RecommendationRead], **kwargs):
        super().__init__(recommendations=recommendations, total=len(recommendations), **kwargs)
