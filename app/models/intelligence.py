"""Intelligence models for dashboard analytics."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


if TYPE_CHECKING:
    from app.models.candidate import Candidate
    from app.models.job import Job
    from app.models.skill import Skill
    from app.models.user import User


class JobIntelligence(Base):
    """Job intelligence analytics for hiring difficulty and market conditions."""

    __tablename__ = "job_intelligence"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )

    hiring_difficulty_score: Mapped[float] = mapped_column(Float, nullable=False)
    candidate_availability_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    skill_scarcity_index: Mapped[float] = mapped_column(Float, nullable=False)
    avg_match_score: Mapped[float] = mapped_column(Float, nullable=False)

    breakdown: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_job_intelligence_job_id", "job_id"),
    )


class CandidateIntelligence(Base):
    """Candidate intelligence analytics for market competitiveness."""

    __tablename__ = "candidate_intelligence"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )

    market_competitiveness_score: Mapped[float] = mapped_column(Float, nullable=False)
    versatility_index: Mapped[float] = mapped_column(Float, nullable=False)
    skill_depth_score: Mapped[float] = mapped_column(Float, nullable=False)
    growth_potential_score: Mapped[float] = mapped_column(Float, nullable=False)

    breakdown: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_candidate_intelligence_candidate_id", "candidate_id"),
    )


class SkillIntelligence(Base):
    """Skill intelligence analytics for market demand and supply."""

    __tablename__ = "skill_intelligence"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )

    demand_count: Mapped[int] = mapped_column(Integer, nullable=False)
    supply_count: Mapped[int] = mapped_column(Integer, nullable=False)
    scarcity_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    avg_required_level: Mapped[float] = mapped_column(Float, nullable=False)

    breakdown: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_skill_intelligence_skill_id", "skill_id"),
    )


class MatchIntelligence(Base):
    """Match intelligence analytics for overall matching quality."""

    __tablename__ = "match_intelligence"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    score_distribution: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )

    top_percentile_score: Mapped[float] = mapped_column(Float, nullable=False)
    low_match_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    recommendation_quality_index: Mapped[float] = mapped_column(Float, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class RecruiterPerformance(Base):
    """Recruiter performance analytics for KPI tracking."""

    __tablename__ = "recruiter_performance"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    recruiter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )

    recommendation_acceptance_rate: Mapped[float] = mapped_column(Float, nullable=False)
    avg_time_to_hire: Mapped[float] = mapped_column(Float, nullable=False)
    hire_success_rate: Mapped[float] = mapped_column(Float, nullable=False)

    breakdown: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_recruiter_performance_recruiter_id", "recruiter_id"),
    )
