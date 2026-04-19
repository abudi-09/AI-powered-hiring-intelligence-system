from __future__ import annotations

import uuid
from typing import Iterable

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job
from app.models.job import JobStatus
from app.models.job_skill import JobSkill
from app.models.skill import Skill
from app.schemas.job import JobCreate, JobUpdate


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


async def list_jobs(
    db: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 50,
    q: str | None = None,
    status: JobStatus | None = None,
) -> tuple[list[Job], int]:
    query = select(Job)
    if q:
        pattern = f"%{q.strip()}%"
        query = query.where(Job.title.ilike(pattern))
    if status is not None:
        query = query.where(Job.status == status.value)

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = int(count_result.scalar_one())

    result = await db.execute(
        query.order_by(Job.created_at.desc()).offset(skip).limit(limit)
    )
    return list(result.scalars().all()), total


async def create_job(db: AsyncSession, payload: JobCreate, owner_id: uuid.UUID) -> Job:
    skills_payload = []
    if payload.skills:
        skills_payload = [{"skill_id": s.skill_id, "weight": s.weight} for s in payload.skills]
        await _validate_skills_exist(db, [item["skill_id"] for item in skills_payload])

    job = Job(
        title=payload.title,
        description=payload.description,
        owner_id=owner_id,
        status=payload.status.value,
    )
    db.add(job)
    await db.flush()

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
    if payload.status is not None:
        job.status = payload.status.value

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
