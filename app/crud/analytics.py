from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.analytics_engine import AnalyticsEngine


async def get_job_analytics(db: AsyncSession, job_id: uuid.UUID) -> dict:
    """Get analytics for a specific job."""
    engine = AnalyticsEngine(db)
    analytics = await engine.compute_job_analytics(job_id)
    
    if analytics is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )
    
    return analytics


async def get_candidate_analytics(db: AsyncSession, candidate_id: uuid.UUID) -> dict:
    """Get analytics for a specific candidate."""
    engine = AnalyticsEngine(db)
    analytics = await engine.compute_candidate_analytics(candidate_id)
    
    if analytics is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found",
        )
    
    return analytics


async def get_skill_demand(db: AsyncSession) -> list[dict]:
    """Get skill demand/supply analytics."""
    engine = AnalyticsEngine(db)
    return await engine.compute_skill_demand()


async def get_skill_scarcity(db: AsyncSession) -> list[dict]:
    """Get scarce skills (high demand, low supply)."""
    engine = AnalyticsEngine(db)
    return await engine.compute_skill_scarcity()


async def get_match_distribution(db: AsyncSession) -> dict:
    """Get match score distribution statistics."""
    engine = AnalyticsEngine(db)
    return await engine.compute_match_distribution()
