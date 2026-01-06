from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MatchScoreRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    candidate_id: uuid.UUID
    job_id: uuid.UUID
    score: float
    explanation: dict | None
    created_at: datetime


class MatchScoreUpsert(BaseModel):
    candidate_id: uuid.UUID
    job_id: uuid.UUID
    score: float = Field(ge=0, le=100)
    explanation: dict | None = None


class MatchAutoScoreRequest(BaseModel):
    candidate_id: uuid.UUID
    job_id: uuid.UUID
