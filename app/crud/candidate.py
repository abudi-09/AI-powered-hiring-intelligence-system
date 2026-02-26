from __future__ import annotations

import uuid
from typing import Iterable

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate
from app.models.candidate_skill import CandidateSkill
from app.models.skill import Skill
from app.schemas.candidate import CandidateCreate, CandidateUpdate


async def _validate_skills_exist(db: AsyncSession, skill_ids: Iterable[uuid.UUID]) -> None:
    ids = list(skill_ids)
    if not ids:
        return
    if len(set(ids)) != len(ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duplicate skill IDs in request",
        )
    result = await db.execute(select(Skill.id).where(Skill.id.in_(ids)))
    existing = set(result.scalars().all())
    if len(existing) != len(set(ids)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="One or more skills not found")


async def _replace_candidate_skills(db: AsyncSession, candidate: Candidate, skills: list[dict] | None) -> None:
    candidate.skill_links.clear()

    if not skills:
        return

    await _validate_skills_exist(db, [item["skill_id"] for item in skills])

    for item in skills:
        candidate.skill_links.append(
            CandidateSkill(
                candidate_id=candidate.id,
                skill_id=item["skill_id"],
                level=item.get("level"),
                years_experience=item.get("years_experience"),
            )
        )


async def get_candidate_by_id(db: AsyncSession, candidate_id: uuid.UUID) -> Candidate:
    result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
    candidate = result.scalar_one_or_none()
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    return candidate


async def list_candidates(db: AsyncSession) -> list[Candidate]:
    result = await db.execute(select(Candidate).order_by(Candidate.created_at.desc()))
    return list(result.scalars().all())


async def create_candidate(db: AsyncSession, payload: CandidateCreate) -> Candidate:
    skills_payload = []
    if payload.skills:
        skills_payload = [
            {
                "skill_id": s.skill_id,
                "level": s.level,
                "years_experience": s.years_experience,
            }
            for s in payload.skills
        ]
        await _validate_skills_exist(db, [item["skill_id"] for item in skills_payload])

    candidate = Candidate(
        full_name=payload.full_name,
        email=str(payload.email) if payload.email is not None else None,
        resume_path=payload.resume_path,
    )
    db.add(candidate)
    await db.flush()

    await _replace_candidate_skills(db, candidate, skills_payload)

    await db.commit()
    await db.refresh(candidate)
    return candidate


async def update_candidate(db: AsyncSession, candidate_id: uuid.UUID, payload: CandidateUpdate) -> Candidate:
    candidate = await get_candidate_by_id(db, candidate_id)

    if payload.full_name is not None:
        candidate.full_name = payload.full_name
    if payload.email is not None:
        candidate.email = str(payload.email) if payload.email else None
    if payload.resume_path is not None:
        candidate.resume_path = payload.resume_path

    if payload.skills is not None:
        skills_payload = [
            {
                "skill_id": s.skill_id,
                "level": s.level,
                "years_experience": s.years_experience,
            }
            for s in payload.skills
        ]
        await _replace_candidate_skills(db, candidate, skills_payload)

    await db.commit()
    await db.refresh(candidate)
    return candidate


async def merge_candidate_skills(
    db: AsyncSession,
    candidate: Candidate,
    skills: list[dict],
) -> None:
    if not skills:
        return

    await _validate_skills_exist(db, [item["skill_id"] for item in skills])
    existing_by_skill = {link.skill_id: link for link in candidate.skill_links}

    for item in skills:
        skill_id = item["skill_id"]
        existing = existing_by_skill.get(skill_id)
        if existing is None:
            candidate.skill_links.append(
                CandidateSkill(
                    candidate_id=candidate.id,
                    skill_id=skill_id,
                    level=item.get("level"),
                    years_experience=item.get("years_experience"),
                )
            )
            continue

        if item.get("level") is not None:
            existing.level = item["level"]
        if item.get("years_experience") is not None:
            existing.years_experience = item["years_experience"]


async def delete_candidate(db: AsyncSession, candidate_id: uuid.UUID) -> None:
    candidate = await get_candidate_by_id(db, candidate_id)
    await db.delete(candidate)
    await db.commit()
