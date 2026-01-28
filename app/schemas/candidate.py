from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.candidate_skill import CandidateSkillInput, CandidateSkillRead


class CandidateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: str | None
    resume_path: str | None
    skills: list[CandidateSkillRead]
    created_at: datetime
    updated_at: datetime


class CandidateCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    email: EmailStr | None = None
    resume_path: str | None = Field(default=None, max_length=1024)
    skills: list[CandidateSkillInput] | None = Field(default_factory=list)


class CandidateUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    email: EmailStr | None = None
    resume_path: str | None = Field(default=None, max_length=1024)
    skills: list[CandidateSkillInput] | None = None


class ResumeSkillExtractionRead(BaseModel):
    extracted_count: int
    candidate: CandidateRead
