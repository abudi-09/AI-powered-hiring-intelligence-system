from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class CandidateSkillInput(BaseModel):
    skill_id: uuid.UUID
    level: str | None = Field(default=None, max_length=50)
    years_experience: float | None = Field(default=None, ge=0)


class CandidateSkillRead(BaseModel):
    skill_id: uuid.UUID
    skill_name: str
    level: str | None
    years_experience: float | None
