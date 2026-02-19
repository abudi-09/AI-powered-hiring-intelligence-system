from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, role_required
from app.db.session import get_db
from app.models.job import Job
from app.models.job_skill import JobSkill
from app.models.skill import Skill
from app.models.user import User, UserRole
from app.schemas.job import JobCreate, JobRead, JobUpdate, JobSkillRead
from app.schemas.match import JobBatchAutoScoreRequest, JobBatchAutoScoreResponse
from app.crud.job import create_job as crud_create_job, delete_job as crud_delete_job, list_jobs as crud_list_jobs, update_job as crud_update_job, get_job_by_id as crud_get_job_by_id
from app.crud.match import batch_auto_score_job_matches


router = APIRouter(prefix="/jobs", tags=["jobs"])


AllowedRoleDep = role_required(UserRole.Admin, UserRole.Recruiter, UserRole.HiringManager)


async def _job_to_read(db: AsyncSession, job: Job) -> JobRead:
    # Load job skills with names via join on Skill
    result = await db.execute(
        select(JobSkill.skill_id, Skill.name, JobSkill.weight)
        .join(Skill, Skill.id == JobSkill.skill_id)
        .where(JobSkill.job_id == job.id)
        .order_by(Skill.name.asc())
    )

    skills_out: list[JobSkillRead] = []
    for skill_id, skill_name, weight in result.all():
        skills_out.append(JobSkillRead(skill_id=skill_id, skill_name=skill_name, weight=weight))

    return JobRead(
        id=job.id,
        title=job.title,
        description=job.description,
        owner_id=job.owner_id,
        skills=skills_out,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


## association management now handled in CRUD layer


@router.get("/", response_model=list[JobRead])
async def list_jobs(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(AllowedRoleDep),
) -> list[JobRead]:
    jobs = await crud_list_jobs(db)
    return [await _job_to_read(db, job) for job in jobs]


@router.post("/", response_model=JobRead, status_code=status.HTTP_201_CREATED)
async def create_job(
    payload: JobCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: User = Depends(AllowedRoleDep),
) -> JobRead:
    job = await crud_create_job(db, payload, owner_id=current_user.id)
    return await _job_to_read(db, job)


@router.get("/{job_id}", response_model=JobRead)
async def get_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(AllowedRoleDep),
) -> JobRead:
    job = await crud_get_job_by_id(db, job_id)
    return await _job_to_read(db, job)


@router.patch("/{job_id}", response_model=JobRead)
async def update_job(
    job_id: uuid.UUID,
    payload: JobUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(AllowedRoleDep),
) -> JobRead:
    job = await crud_update_job(db, job_id, payload)
    return await _job_to_read(db, job)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(AllowedRoleDep),
) -> None:
    await crud_delete_job(db, job_id)
    return None


@router.post(
    "/{job_id}/matches/auto-score",
    response_model=JobBatchAutoScoreResponse,
    status_code=status.HTTP_201_CREATED,
)
async def auto_score_job_matches(
    job_id: uuid.UUID,
    payload: JobBatchAutoScoreRequest | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(AllowedRoleDep),
) -> JobBatchAutoScoreResponse:
    """Calculate and store match scores for all candidates against a job."""
    candidate_ids = payload.candidate_ids if payload is not None else None
    matches = await batch_auto_score_job_matches(db, job_id, candidate_ids)
    return JobBatchAutoScoreResponse(
        job_id=job_id,
        scored_count=len(matches),
        matches=matches,
    )
