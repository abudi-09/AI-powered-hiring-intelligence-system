from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import role_required
from app.db.session import get_db
from app.models.match import MatchScore
from app.models.user import User, UserRole
from app.schemas.match import (
    MatchScoreAutoRequest,
    MatchScoreCreate,
    MatchScoreRead,
)
from app.crud.match import (
    calculate_match_score,
    get_matches_by_candidate,
    get_matches_by_job,
    get_top_candidates,
    get_top_jobs,
    upsert_match_score,
)


router = APIRouter(prefix="/matches", tags=["matches"])


AllowedRoleDep = role_required(UserRole.Admin, UserRole.Recruiter, UserRole.HiringManager)


@router.post("/auto-score", response_model=MatchScoreRead, status_code=status.HTTP_201_CREATED)
async def auto_score_match(
    payload: MatchScoreAutoRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(AllowedRoleDep),
) -> MatchScore:
    """Automatically calculate and store match score using AI engine."""
    score, explanation = await calculate_match_score(
        db, payload.candidate_id, payload.job_id
    )
    
    match = await upsert_match_score(
        db,
        payload.candidate_id,
        payload.job_id,
        score,
        explanation,
    )
    
    return match


@router.post("/manual", response_model=MatchScoreRead, status_code=status.HTTP_201_CREATED)
async def manual_score_match(
    payload: MatchScoreCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(AllowedRoleDep),
) -> MatchScore:
    """Manually create or update a match score."""
    match = await upsert_match_score(
        db,
        payload.candidate_id,
        payload.job_id,
        payload.score,
        payload.explanation,
    )
    
    return match


@router.get("/by-job/{job_id}", response_model=list[MatchScoreRead])
async def list_matches_for_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(AllowedRoleDep),
) -> list[MatchScore]:
    """Get all match scores for a specific job."""
    return await get_matches_by_job(db, job_id)


@router.get("/by-candidate/{candidate_id}", response_model=list[MatchScoreRead])
async def list_matches_for_candidate(
    candidate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(AllowedRoleDep),
) -> list[MatchScore]:
    """Get all match scores for a specific candidate."""
    return await get_matches_by_candidate(db, candidate_id)


@router.get("/top-candidates/{job_id}", response_model=list[MatchScoreRead])
async def top_candidates_for_job(
    job_id: uuid.UUID,
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(AllowedRoleDep),
) -> list[MatchScore]:
    """Get top N candidates for a job ranked by match score."""
    return await get_top_candidates(db, job_id, limit)


@router.get("/top-jobs/{candidate_id}", response_model=list[MatchScoreRead])
async def top_jobs_for_candidate(
    candidate_id: uuid.UUID,
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(AllowedRoleDep),
) -> list[MatchScore]:
    """Get top N jobs for a candidate ranked by match score."""
    return await get_top_jobs(db, candidate_id, limit)
