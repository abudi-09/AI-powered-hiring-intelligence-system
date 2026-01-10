from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_async_db, role_required
from app.models.recommendation import Recommendation
from app.models.user import User, UserRole
from app.schemas.narrative import (
    NarrativeRequest,
    BatchNarrativeRequest,
    NarrativeRead,
    BatchNarrativeRead,
)
from app.services.narrative_engine import NarrativeEngine

router = APIRouter(prefix="/narratives", tags=["narratives"])

AllowedRoleDep = role_required(
    UserRole.Admin, UserRole.Recruiter, UserRole.HiringManager
)


@router.post("/recommendation/{recommendation_id}", response_model=NarrativeRead)
async def generate_recommendation_narrative(
    recommendation_id: uuid.UUID,
    request: NarrativeRequest,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    _: User = Depends(AllowedRoleDep),
):
    """Generate human-readable narrative for a recommendation."""
    result = await db.execute(
        select(Recommendation).where(Recommendation.id == recommendation_id)
    )
    recommendation = result.scalar_one_or_none()

    if not recommendation:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    engine = NarrativeEngine()
    narrative_data = await engine.generate_narrative(
        recommendation=recommendation,
        tone=request.tone.value,
        include_bullets=request.include_bullets,
    )

    return NarrativeRead(**narrative_data)


@router.post("/batch", response_model=BatchNarrativeRead)
async def generate_batch_narratives(
    request: BatchNarrativeRequest,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    _: User = Depends(AllowedRoleDep),
):
    """Generate narratives for multiple recommendations."""
    result = await db.execute(
        select(Recommendation).where(Recommendation.id.in_(request.recommendation_ids))
    )
    recommendations = result.scalars().all()

    if not recommendations:
        raise HTTPException(status_code=404, detail="No recommendations found")

    engine = NarrativeEngine()
    narratives = []

    for recommendation in recommendations:
        narrative_data = await engine.generate_narrative(
            recommendation=recommendation,
            tone=request.tone.value,
            include_bullets=request.include_bullets,
        )
        narratives.append(NarrativeRead(**narrative_data))

    return BatchNarrativeRead(narratives=narratives)
