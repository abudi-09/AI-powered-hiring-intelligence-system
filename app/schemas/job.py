from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class JobSkillInput(BaseModel):
    skill_id: uuid.UUID
    weight: float | None = Field(default=None, ge=0, le=1)


class JobSkillRead(BaseModel):
    skill_id: uuid.UUID
    skill_name: str
    weight: float | None


class JobRead(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    owner_id: uuid.UUID
    skills: list[JobSkillRead]
    created_at: datetime
    updated_at: datetime


class JobCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None)
    skills: list[JobSkillInput] | None = Field(default_factory=list)


class JobUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    skills: list[JobSkillInput] | None = None
