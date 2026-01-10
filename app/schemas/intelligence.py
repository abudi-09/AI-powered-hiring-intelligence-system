"""Intelligence schemas for dashboard analytics."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# Job Intelligence Schemas
class JobIntelligenceRead(BaseModel):
    """Job intelligence read schema."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_id: UUID
    hiring_difficulty_score: float = Field(ge=0, le=100)
    candidate_availability_ratio: float = Field(ge=0)
    skill_scarcity_index: float = Field(ge=0, le=100)
    avg_match_score: float = Field(ge=0, le=100)
    breakdown: dict
    created_at: datetime


class JobIntelligenceList(BaseModel):
    """Job intelligence list schema."""

    model_config = ConfigDict(from_attributes=True)

    items: list[JobIntelligenceRead]
    total: int


# Candidate Intelligence Schemas
class CandidateIntelligenceRead(BaseModel):
    """Candidate intelligence read schema."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    candidate_id: UUID
    market_competitiveness_score: float = Field(ge=0, le=100)
    versatility_index: float = Field(ge=0, le=100)
    skill_depth_score: float = Field(ge=0, le=100)
    growth_potential_score: float = Field(ge=0, le=100)
    breakdown: dict
    created_at: datetime


class CandidateIntelligenceList(BaseModel):
    """Candidate intelligence list schema."""

    model_config = ConfigDict(from_attributes=True)

    items: list[CandidateIntelligenceRead]
    total: int


# Skill Intelligence Schemas
class SkillIntelligenceRead(BaseModel):
    """Skill intelligence read schema."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    skill_id: UUID
    demand_count: int = Field(ge=0)
    supply_count: int = Field(ge=0)
    scarcity_ratio: float = Field(ge=0)
    avg_required_level: float = Field(ge=0, le=100)
    breakdown: dict
    created_at: datetime


class SkillIntelligenceList(BaseModel):
    """Skill intelligence list schema."""

    model_config = ConfigDict(from_attributes=True)

    items: list[SkillIntelligenceRead]
    total: int


# Match Intelligence Schemas
class MatchIntelligenceRead(BaseModel):
    """Match intelligence read schema."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    score_distribution: dict
    top_percentile_score: float = Field(ge=0, le=100)
    low_match_ratio: float = Field(ge=0, le=100)
    recommendation_quality_index: float = Field(ge=0, le=100)
    created_at: datetime


class MatchIntelligenceList(BaseModel):
    """Match intelligence list schema."""

    model_config = ConfigDict(from_attributes=True)

    items: list[MatchIntelligenceRead]
    total: int


# Recruiter Performance Schemas
class RecruiterPerformanceRead(BaseModel):
    """Recruiter performance read schema."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    recruiter_id: UUID
    recommendation_acceptance_rate: float = Field(ge=0, le=100)
    avg_time_to_hire: float = Field(ge=0)
    hire_success_rate: float = Field(ge=0, le=100)
    breakdown: dict
    created_at: datetime


class RecruiterPerformanceList(BaseModel):
    """Recruiter performance list schema."""

    model_config = ConfigDict(from_attributes=True)

    items: list[RecruiterPerformanceRead]
    total: int
