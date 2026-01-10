from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.recommendation import Recommendation
from app.services.recommendation_engine import RecommendationEngine


async def create_recommendation(
    db: AsyncSession,
    entity_type: str,
    entity_id: uuid.UUID,
    recommended_entity_id: uuid.UUID,
    recommendation_type: str,
    rank: int,
    score: float,
    confidence: float,
    explanation: dict,
) -> Recommendation:
    """Create a new recommendation."""
    recommendation = Recommendation(
        entity_type=entity_type,
        entity_id=entity_id,
        recommended_entity_id=recommended_entity_id,
        recommendation_type=recommendation_type,
        rank=rank,
        score=score,
        confidence=confidence,
        explanation=explanation,
    )
    db.add(recommendation)
    await db.commit()
    await db.refresh(recommendation)
    return recommendation


async def list_recommendations(
    db: AsyncSession, entity_type: str, entity_id: uuid.UUID
) -> Sequence[Recommendation]:
    """List all recommendations for an entity."""
    result = await db.execute(
        select(Recommendation)
        .where(
            Recommendation.entity_type == entity_type,
            Recommendation.entity_id == entity_id,
        )
        .order_by(Recommendation.rank.asc())
    )
    return result.scalars().all()


async def delete_recommendation(db: AsyncSession, recommendation_id: uuid.UUID) -> bool:
    """Delete a recommendation by ID."""
    result = await db.execute(
        delete(Recommendation).where(Recommendation.id == recommendation_id)
    )
    await db.commit()
    return result.rowcount > 0


async def generate_recommendations_for_job(
    db: AsyncSession, job_id: uuid.UUID, limit: int = 10
) -> Sequence[Recommendation]:
    """Generate and persist candidate recommendations for a job."""
    await db.execute(
        delete(Recommendation).where(
            Recommendation.entity_type == "job", Recommendation.entity_id == job_id
        )
    )
    await db.commit()

    engine = RecommendationEngine(db)
    rec_data_list = await engine.generate_job_recommendations(job_id, limit)

    recommendations = []
    for data in rec_data_list:
        rec = await create_recommendation(
            db=db,
            entity_type=data["entity_type"],
            entity_id=data["entity_id"],
            recommended_entity_id=data["recommended_entity_id"],
            recommendation_type=data["recommendation_type"],
            rank=data["rank"],
            score=data["score"],
            confidence=data["confidence"],
            explanation=data["explanation"],
        )
        recommendations.append(rec)

    return recommendations


async def generate_recommendations_for_candidate(
    db: AsyncSession, candidate_id: uuid.UUID, limit: int = 10
) -> Sequence[Recommendation]:
    """Generate and persist job recommendations for a candidate."""
    await db.execute(
        delete(Recommendation).where(
            Recommendation.entity_type == "candidate",
            Recommendation.entity_id == candidate_id,
        )
    )
    await db.commit()

    engine = RecommendationEngine(db)
    rec_data_list = await engine.generate_candidate_recommendations(candidate_id, limit)

    recommendations = []
    for data in rec_data_list:
        rec = await create_recommendation(
            db=db,
            entity_type=data["entity_type"],
            entity_id=data["entity_id"],
            recommended_entity_id=data["recommended_entity_id"],
            recommendation_type=data["recommendation_type"],
            rank=data["rank"],
            score=data["score"],
            confidence=data["confidence"],
            explanation=data["explanation"],
        )
        recommendations.append(rec)

    return recommendations
