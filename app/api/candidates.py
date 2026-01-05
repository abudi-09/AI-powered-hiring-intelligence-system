from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import role_required
from app.db.session import get_db
from app.models.candidate import Candidate
from app.models.skill import Skill
from app.models.user import User, UserRole
from app.schemas.candidate import CandidateCreate, CandidateRead, CandidateUpdate


router = APIRouter(prefix="/candidates", tags=["candidates"])


AllowedRoleDep = role_required(UserRole.Admin, UserRole.Recruiter, UserRole.HiringManager)


@router.get("/", response_model=list[CandidateRead])
async def list_candidates(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(AllowedRoleDep),
) -> list[Candidate]:
    result = await db.execute(select(Candidate).order_by(Candidate.created_at.desc()))
    return list(result.scalars().all())


@router.post("/", response_model=CandidateRead, status_code=status.HTTP_201_CREATED)
async def create_candidate(
    payload: CandidateCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(AllowedRoleDep),
) -> Candidate:
    candidate = Candidate(
        full_name=payload.full_name,
        email=str(payload.email) if payload.email is not None else None,
        resume_path=payload.resume_path,
    )

    if payload.skill_ids:
        result = await db.execute(select(Skill).where(Skill.id.in_(payload.skill_ids)))
        skills = list(result.scalars().all())
        if len(skills) != len(set(payload.skill_ids)):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="One or more skills not found")
        candidate.skills = skills

    db.add(candidate)
    await db.commit()
    await db.refresh(candidate)
    return candidate


@router.get("/{candidate_id}", response_model=CandidateRead)
async def get_candidate(
    candidate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(AllowedRoleDep),
) -> Candidate:
    result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
    candidate = result.scalar_one_or_none()
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    return candidate


@router.patch("/{candidate_id}", response_model=CandidateRead)
async def update_candidate(
    candidate_id: uuid.UUID,
    payload: CandidateUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(AllowedRoleDep),
) -> Candidate:
    result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
    candidate = result.scalar_one_or_none()
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    if payload.full_name is not None:
        candidate.full_name = payload.full_name
    if payload.email is not None:
        candidate.email = str(payload.email)
    if payload.resume_path is not None:
        candidate.resume_path = payload.resume_path

    if payload.skill_ids is not None:
        if payload.skill_ids:
            skills_result = await db.execute(select(Skill).where(Skill.id.in_(payload.skill_ids)))
            skills = list(skills_result.scalars().all())
            if len(skills) != len(set(payload.skill_ids)):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="One or more skills not found")
            candidate.skills = skills
        else:
            candidate.skills = []

    await db.commit()
    await db.refresh(candidate)
    return candidate


@router.delete("/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_candidate(
    candidate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(AllowedRoleDep),
) -> None:
    result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
    candidate = result.scalar_one_or_none()
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    await db.delete(candidate)
    await db.commit()
    return None
