from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import role_required
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.analytics import (
    CandidateAnalyticsRead,
    JobAnalyticsRead,
    MatchDistributionRead,
    SkillDemandRead,
)
from app.crud.analytics import (
    get_candidate_analytics,
    get_job_analytics,
    get_match_distribution,
    get_skill_demand,
    get_skill_scarcity,
)


router = APIRouter(prefix="/analytics", tags=["analytics"])


AllowedRoleDep = role_required(UserRole.Admin, UserRole.Recruiter, UserRole.HiringManager)


@router.get("/jobs/{job_id}", response_model=JobAnalyticsRead)
async def get_job_analytics_endpoint(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(AllowedRoleDep),
) -> dict:
    """Get comprehensive analytics for a specific job."""
    return await get_job_analytics(db, job_id)


@router.get("/candidates/{candidate_id}", response_model=CandidateAnalyticsRead)
async def get_candidate_analytics_endpoint(
    candidate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(AllowedRoleDep),
) -> dict:
    """Get comprehensive analytics for a specific candidate."""
    return await get_candidate_analytics(db, candidate_id)


@router.get("/skills/demand", response_model=list[SkillDemandRead])
async def get_skill_demand_endpoint(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(AllowedRoleDep),
) -> list[dict]:
    """Get skill demand and supply analytics across all skills."""
    return await get_skill_demand(db)


@router.get("/skills/scarcity", response_model=list[SkillDemandRead])
async def get_skill_scarcity_endpoint(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(AllowedRoleDep),
) -> list[dict]:
    """Get scarce skills (high demand, low supply ratio > 1.0)."""
    return await get_skill_scarcity(db)


@router.get("/matches/distribution", response_model=MatchDistributionRead)
async def get_match_distribution_endpoint(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(AllowedRoleDep),
) -> dict:
    """Get match score distribution statistics across all matches."""
    return await get_match_distribution(db)
