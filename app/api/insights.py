from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_async_db, role_required
from app.crud import insight as insight_crud
from app.models.user import User, UserRole
from app.schemas.insight import InsightRead, InsightList

router = APIRouter(prefix="/insights", tags=["insights"])

AllowedRoleDep = role_required(UserRole.Admin, UserRole.Recruiter, UserRole.HiringManager)


@router.get("/job/{job_id}", response_model=InsightList)
async def get_job_insights(
    job_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    _: User = Depends(AllowedRoleDep),
):
    """Get all insights for a job."""
    insights = await insight_crud.list_insights_by_entity(db, "job", job_id)
    return InsightList(insights=[InsightRead.model_validate(i) for i in insights])


@router.get("/candidate/{candidate_id}", response_model=InsightList)
async def get_candidate_insights(
    candidate_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    _: User = Depends(AllowedRoleDep),
):
    """Get all insights for a candidate."""
    insights = await insight_crud.list_insights_by_entity(db, "candidate", candidate_id)
    return InsightList(insights=[InsightRead.model_validate(i) for i in insights])


@router.post("/generate/job/{job_id}", response_model=InsightList)
async def generate_job_insights(
    job_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    _: User = Depends(AllowedRoleDep),
):
    """Auto-generate and persist insights for a job."""
    insights = await insight_crud.auto_generate_insights_for_job(db, job_id)
    return InsightList(insights=[InsightRead.model_validate(i) for i in insights])


@router.post("/generate/candidate/{candidate_id}", response_model=InsightList)
async def generate_candidate_insights(
    candidate_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    _: User = Depends(AllowedRoleDep),
):
    """Auto-generate and persist insights for a candidate."""
    insights = await insight_crud.auto_generate_insights_for_candidate(db, candidate_id)
    return InsightList(insights=[InsightRead.model_validate(i) for i in insights])


@router.delete("/{insight_id}")
async def delete_insight(
    insight_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    _: User = Depends(AllowedRoleDep),
):
    """Delete an insight."""
    deleted = await insight_crud.delete_insight(db, insight_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Insight not found")
    return {"message": "Insight deleted successfully"}
