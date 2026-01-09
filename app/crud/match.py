from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate
from app.models.job import Job
from app.models.match import MatchScore
from app.schemas.match import MatchScoreCreate
from app.services.match_engine import MatchEngine


async def calculate_match_score(
    db: AsyncSession, candidate_id: uuid.UUID, job_id: uuid.UUID
) -> tuple[float, dict]:
    """Calculate match score using AI engine."""
    await _validate_candidate_exists(db, candidate_id)
    await _validate_job_exists(db, job_id)
    
    engine = MatchEngine(db)
    score, explanation = await engine.calculate_match_score(candidate_id, job_id)
    return score, explanation


async def upsert_match_score(
    db: AsyncSession,
    candidate_id: uuid.UUID,
    job_id: uuid.UUID,
    score: float,
    explanation: dict | None,
) -> MatchScore:
    """Insert or update match score."""
    await _validate_candidate_exists(db, candidate_id)
    await _validate_job_exists(db, job_id)
    
    stmt = (
        insert(MatchScore)
        .values(
            candidate_id=candidate_id,
            job_id=job_id,
            score=score,
            explanation=explanation,
        )
        .on_conflict_do_update(
            index_elements=[MatchScore.candidate_id, MatchScore.job_id],
            set_={
                "score": score,
                "explanation": explanation,
            },
        )
        .returning(MatchScore)
    )
    
    result = await db.execute(stmt)
    await db.commit()
    row = result.fetchone()
    
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upsert match score",
        )
    
    return row[0]


async def get_matches_by_job(db: AsyncSession, job_id: uuid.UUID) -> list[MatchScore]:
    """Get all matches for a job, ordered by score descending."""
    result = await db.execute(
        select(MatchScore)
        .where(MatchScore.job_id == job_id)
        .order_by(MatchScore.score.desc(), MatchScore.created_at.desc())
    )
    return list(result.scalars().all())


async def get_matches_by_candidate(
    db: AsyncSession, candidate_id: uuid.UUID
) -> list[MatchScore]:
    """Get all matches for a candidate, ordered by score descending."""
    result = await db.execute(
        select(MatchScore)
        .where(MatchScore.candidate_id == candidate_id)
        .order_by(MatchScore.score.desc(), MatchScore.created_at.desc())
    )
    return list(result.scalars().all())


async def get_top_candidates(
    db: AsyncSession, job_id: uuid.UUID, limit: int = 10
) -> list[MatchScore]:
    """Get top N candidates for a job by score."""
    result = await db.execute(
        select(MatchScore)
        .where(MatchScore.job_id == job_id)
        .order_by(MatchScore.score.desc(), MatchScore.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_top_jobs(
    db: AsyncSession, candidate_id: uuid.UUID, limit: int = 10
) -> list[MatchScore]:
    """Get top N jobs for a candidate by score."""
    result = await db.execute(
        select(MatchScore)
        .where(MatchScore.candidate_id == candidate_id)
        .order_by(MatchScore.score.desc(), MatchScore.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def _validate_candidate_exists(db: AsyncSession, candidate_id: uuid.UUID) -> None:
    """Validate candidate exists."""
    result = await db.execute(select(Candidate.id).where(Candidate.id == candidate_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Candidate not found",
        )


async def _validate_job_exists(db: AsyncSession, job_id: uuid.UUID) -> None:
    """Validate job exists."""
    result = await db.execute(select(Job.id).where(Job.id == job_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job not found",
        )
