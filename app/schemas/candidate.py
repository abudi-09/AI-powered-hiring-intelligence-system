from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.skill import SkillRead


class CandidateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: str | None
    resume_path: str | None
    skills: list[SkillRead]
    created_at: datetime
    updated_at: datetime


class CandidateCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    email: EmailStr | None = None
    resume_path: str | None = Field(default=None, max_length=1024)
    skill_ids: list[uuid.UUID] = Field(default_factory=list)


class CandidateUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    email: EmailStr | None = None
    resume_path: str | None = Field(default=None, max_length=1024)
    skill_ids: list[uuid.UUID] | None = None
