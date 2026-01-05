from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, role_required
from app.db.session import get_db
from app.models.job import Job
from app.models.skill import Skill, job_skills
from app.models.user import User, UserRole
from app.schemas.job import JobCreate, JobRead, JobUpdate, JobSkillOut
from app.schemas.skill import SkillRead


router = APIRouter(prefix="/jobs", tags=["jobs"])


AllowedRoleDep = role_required(UserRole.Admin, UserRole.Recruiter, UserRole.HiringManager)


async def _job_to_read(db: AsyncSession, job: Job) -> JobRead:
    # Load job skill weights + skill details
    result = await db.execute(
        select(Skill, job_skills.c.weight)
        .join(job_skills, job_skills.c.skill_id == Skill.id)
        .where(job_skills.c.job_id == job.id)
        .order_by(Skill.name.asc())
    )

    skills_out: list[JobSkillOut] = []
    for skill, weight in result.all():
        skills_out.append(JobSkillOut(skill=SkillRead.model_validate(skill), weight=weight))

    return JobRead(
        id=job.id,
        title=job.title,
        description=job.description,
        owner_id=job.owner_id,
        skills=skills_out,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


async def _set_job_skills(db: AsyncSession, job: Job, skills: list[dict]) -> None:
    # Clear existing
    await db.execute(delete(job_skills).where(job_skills.c.job_id == job.id))

    if not skills:
        return

    skill_ids = [item["skill_id"] for item in skills]
    existing = await db.execute(select(Skill.id).where(Skill.id.in_(skill_ids)))
    existing_ids = set(existing.scalars().all())
    if len(existing_ids) != len(set(skill_ids)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="One or more skills not found")

    rows = []
    for item in skills:
        rows.append(
            {
                "job_id": job.id,
                "skill_id": item["skill_id"],
                "weight": item.get("weight"),
            }
        )

    await db.execute(insert(job_skills), rows)


@router.get("/", response_model=list[JobRead])
async def list_jobs(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(AllowedRoleDep),
) -> list[JobRead]:
    result = await db.execute(select(Job).order_by(Job.created_at.desc()))
    jobs = list(result.scalars().all())
    return [await _job_to_read(db, job) for job in jobs]


@router.post("/", response_model=JobRead, status_code=status.HTTP_201_CREATED)
async def create_job(
    payload: JobCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: User = Depends(AllowedRoleDep),
) -> JobRead:
    job = Job(
        title=payload.title,
        description=payload.description,
        owner_id=current_user.id,
    )
    db.add(job)
    await db.flush()

    skills_payload = [{"skill_id": s.skill_id, "weight": s.weight} for s in payload.skills]
    await _set_job_skills(db, job, skills_payload)

    await db.commit()
    await db.refresh(job)
    return await _job_to_read(db, job)


@router.get("/{job_id}", response_model=JobRead)
async def get_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(AllowedRoleDep),
) -> JobRead:
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return await _job_to_read(db, job)


@router.patch("/{job_id}", response_model=JobRead)
async def update_job(
    job_id: uuid.UUID,
    payload: JobUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(AllowedRoleDep),
) -> JobRead:
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    if payload.title is not None:
        job.title = payload.title
    if payload.description is not None:
        job.description = payload.description

    if payload.skills is not None:
        skills_payload = [{"skill_id": s.skill_id, "weight": s.weight} for s in payload.skills]
        await _set_job_skills(db, job, skills_payload)

    await db.commit()
    await db.refresh(job)
    return await _job_to_read(db, job)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(AllowedRoleDep),
) -> None:
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    await db.delete(job)
    await db.commit()
    return None
