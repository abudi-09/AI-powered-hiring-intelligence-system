from __future__ import annotations

import uuid
from typing import Iterable

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job
from app.models.job_skill import JobSkill
from app.models.skill import Skill
from app.schemas.job import JobCreate, JobUpdate


async def _validate_skills_exist(db: AsyncSession, skill_ids: Iterable[uuid.UUID]) -> None:
    ids = list(skill_ids)
    if not ids:
        return
    result = await db.execute(select(Skill.id).where(Skill.id.in_(ids)))
    existing = set(result.scalars().all())
    if len(existing) != len(set(ids)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="One or more skills not found")


async def _replace_job_skills(db: AsyncSession, job: Job, skills: list[dict] | None) -> None:
    # Clear existing associations
    job.skills.clear()

    if not skills:
        return

    await _validate_skills_exist(db, [item["skill_id"] for item in skills])

    for item in skills:
        job.skills.append(
            JobSkill(
                job_id=job.id,
                skill_id=item["skill_id"],
                weight=item.get("weight"),
            )
        )


async def get_job_by_id(db: AsyncSession, job_id: uuid.UUID) -> Job:
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


async def list_jobs(db: AsyncSession) -> list[Job]:
    result = await db.execute(select(Job).order_by(Job.created_at.desc()))
    return list(result.scalars().all())


async def create_job(db: AsyncSession, payload: JobCreate, owner_id: uuid.UUID) -> Job:
    job = Job(title=payload.title, description=payload.description, owner_id=owner_id)
    db.add(job)
    await db.flush()

    skills_payload = []
    if payload.skills:
        skills_payload = [{"skill_id": s.skill_id, "weight": s.weight} for s in payload.skills]

    await _replace_job_skills(db, job, skills_payload)

    await db.commit()
    await db.refresh(job)
    return job


async def update_job(db: AsyncSession, job_id: uuid.UUID, payload: JobUpdate) -> Job:
    job = await get_job_by_id(db, job_id)

    if payload.title is not None:
        job.title = payload.title
    if payload.description is not None:
        job.description = payload.description

    if payload.skills is not None:
        skills_payload = [{"skill_id": s.skill_id, "weight": s.weight} for s in payload.skills]
        await _replace_job_skills(db, job, skills_payload)

    await db.commit()
    await db.refresh(job)
    return job


async def delete_job(db: AsyncSession, job_id: uuid.UUID) -> None:
    job = await get_job_by_id(db, job_id)
    await db.delete(job)
    await db.commit()
