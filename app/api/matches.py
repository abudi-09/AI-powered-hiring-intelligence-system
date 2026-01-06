from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import role_required
from app.db.session import get_db
from app.models.candidate import Candidate
from app.models.job import Job
from app.models.match import MatchScore
from app.models.user import User, UserRole
from app.schemas.match import MatchScoreRead, MatchScoreUpsert


router = APIRouter(prefix="/matches", tags=["matches"])


AllowedRoleDep = role_required(UserRole.Admin, UserRole.Recruiter, UserRole.HiringManager)


@router.post("/", response_model=MatchScoreRead)
async def upsert_match_score(
    payload: MatchScoreUpsert,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(AllowedRoleDep),
) -> MatchScore:
    # Validate FK existence with friendly errors
    cand = await db.execute(select(Candidate.id).where(Candidate.id == payload.candidate_id))
    if cand.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Candidate not found")

    job = await db.execute(select(Job.id).where(Job.id == payload.job_id))
    if job.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Job not found")

    stmt = (
        insert(MatchScore)
        .values(
            candidate_id=payload.candidate_id,
            job_id=payload.job_id,
            score=payload.score,
            explanation=payload.explanation,
        )
        .on_conflict_do_update(
            index_elements=[MatchScore.candidate_id, MatchScore.job_id],
            set_={
                "score": payload.score,
                "explanation": payload.explanation,
            },
        )
        .returning(MatchScore)
    )

    result = await db.execute(stmt)
    await db.commit()
    row = result.fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Upsert failed")

    # row can be a tuple; first element is the ORM instance
    match: MatchScore = row[0]
    return match


@router.get("/by-job/{job_id}", response_model=list[MatchScoreRead])
async def list_matches_for_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(AllowedRoleDep),
) -> list[MatchScore]:
    result = await db.execute(
        select(MatchScore)
        .where(MatchScore.job_id == job_id)
        .order_by(MatchScore.score.desc(), MatchScore.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/by-candidate/{candidate_id}", response_model=list[MatchScoreRead])
async def list_matches_for_candidate(
    candidate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(AllowedRoleDep),
) -> list[MatchScore]:
    result = await db.execute(
        select(MatchScore)
        .where(MatchScore.candidate_id == candidate_id)
        .order_by(MatchScore.score.desc(), MatchScore.created_at.desc())
    )
    return list(result.scalars().all())
