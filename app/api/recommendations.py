from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_async_db, role_required
from app.crud import recommendation as recommendation_crud
from app.models.user import User, UserRole
from app.schemas.recommendation import RecommendationRead, RecommendationList

router = APIRouter(prefix="/recommendations", tags=["recommendations"])

AllowedRoleDep = role_required(
    UserRole.Admin, UserRole.Recruiter, UserRole.HiringManager
)


@router.get("/job/{job_id}", response_model=RecommendationList)
async def get_job_recommendations(
    job_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    _: User = Depends(AllowedRoleDep),
):
    """Get all recommendations for a job."""
    recommendations = await recommendation_crud.list_recommendations(db, "job", job_id)
    return RecommendationList(
        recommendations=[RecommendationRead.model_validate(r) for r in recommendations]
    )


@router.get("/candidate/{candidate_id}", response_model=RecommendationList)
async def get_candidate_recommendations(
    candidate_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    _: User = Depends(AllowedRoleDep),
):
    """Get all recommendations for a candidate."""
    recommendations = await recommendation_crud.list_recommendations(
        db, "candidate", candidate_id
    )
    return RecommendationList(
        recommendations=[RecommendationRead.model_validate(r) for r in recommendations]
    )


@router.post("/generate/job/{job_id}", response_model=RecommendationList)
async def generate_job_recommendations(
    job_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    _: User = Depends(AllowedRoleDep),
    limit: int = Query(default=10, ge=1, le=50),
):
    """Generate and persist candidate recommendations for a job."""
    recommendations = await recommendation_crud.generate_recommendations_for_job(
        db, job_id, limit
    )
    return RecommendationList(
        recommendations=[RecommendationRead.model_validate(r) for r in recommendations]
    )


@router.post("/generate/candidate/{candidate_id}", response_model=RecommendationList)
async def generate_candidate_recommendations(
    candidate_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    _: User = Depends(AllowedRoleDep),
    limit: int = Query(default=10, ge=1, le=50),
):
    """Generate and persist job recommendations for a candidate."""
    recommendations = await recommendation_crud.generate_recommendations_for_candidate(
        db, candidate_id, limit
    )
    return RecommendationList(
        recommendations=[RecommendationRead.model_validate(r) for r in recommendations]
    )


@router.delete("/{recommendation_id}")
async def delete_recommendation(
    recommendation_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    _: User = Depends(AllowedRoleDep),
):
    """Delete a recommendation."""
    deleted = await recommendation_crud.delete_recommendation(db, recommendation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    return {"message": "Recommendation deleted successfully"}
