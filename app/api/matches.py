from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import role_required
from app.db.session import get_db
from app.models.candidate import Candidate
from app.models.job import Job
from app.models.skill import Skill, job_skills
from app.models.match import MatchScore
from app.models.user import User, UserRole
from app.schemas.match import MatchAutoScoreRequest, MatchScoreRead, MatchScoreUpsert


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


@router.post("/auto-score", response_model=MatchScoreRead)
async def auto_score_match(
    payload: MatchAutoScoreRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(AllowedRoleDep),
) -> MatchScore:
    cand_result = await db.execute(
        select(Candidate).options(selectinload(Candidate.skills)).where(Candidate.id == payload.candidate_id)
    )
    candidate = cand_result.scalar_one_or_none()
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Candidate not found")

    job_result = await db.execute(select(Job.id).where(Job.id == payload.job_id))
    if job_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Job not found")

    job_skills_result = await db.execute(
        select(Skill.id, Skill.name, job_skills.c.weight)
        .join(job_skills, job_skills.c.skill_id == Skill.id)
        .where(job_skills.c.job_id == payload.job_id)
        .order_by(Skill.name.asc())
    )

    candidate_skill_ids = {s.id for s in candidate.skills}
    total_weight = 0.0
    matched_weight = 0.0

    matched: list[dict] = []
    missing: list[dict] = []

    for skill_id, skill_name, weight in job_skills_result.all():
        w = float(weight) if weight is not None else 1.0
        if w < 0:
            w = 0.0
        total_weight += w
        if skill_id in candidate_skill_ids:
            matched_weight += w
            matched.append({"skill_id": str(skill_id), "skill": skill_name, "weight": w})
        else:
            missing.append({"skill_id": str(skill_id), "skill": skill_name, "weight": w})

    score = 0.0 if total_weight <= 0 else (matched_weight / total_weight) * 100.0
    if score < 0:
        score = 0.0
    if score > 100:
        score = 100.0

    explanation = {
        "strategy": "skill_overlap_v1",
        "candidate_skill_count": len(candidate_skill_ids),
        "job_skill_count": len(matched) + len(missing),
        "matched": matched,
        "missing": missing,
        "weights": {"matched": matched_weight, "total": total_weight},
    }

    stmt = (
        insert(MatchScore)
        .values(
            candidate_id=payload.candidate_id,
            job_id=payload.job_id,
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
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Upsert failed")

    match: MatchScore = row[0]
    return match


@router.get("/top-candidates/{job_id}", response_model=list[MatchScoreRead])
async def top_candidates_for_job(
    job_id: uuid.UUID,
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(AllowedRoleDep),
) -> list[MatchScore]:
    result = await db.execute(
        select(MatchScore)
        .where(MatchScore.job_id == job_id)
        .order_by(MatchScore.score.desc(), MatchScore.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


@router.get("/top-jobs/{candidate_id}", response_model=list[MatchScoreRead])
async def top_jobs_for_candidate(
    candidate_id: uuid.UUID,
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(AllowedRoleDep),
) -> list[MatchScore]:
    result = await db.execute(
        select(MatchScore)
        .where(MatchScore.candidate_id == candidate_id)
        .order_by(MatchScore.score.desc(), MatchScore.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
