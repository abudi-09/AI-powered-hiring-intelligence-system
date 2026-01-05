from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.skill import SkillRead


class JobSkillIn(BaseModel):
    skill_id: uuid.UUID
    weight: float | None = Field(default=None, ge=0)


class JobSkillOut(BaseModel):
    skill: SkillRead
    weight: float | None


class JobRead(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    owner_id: uuid.UUID
    skills: list[JobSkillOut]
    created_at: datetime
    updated_at: datetime


class JobCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None)
    skills: list[JobSkillIn] = Field(default_factory=list)


class JobUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    skills: list[JobSkillIn] | None = None
