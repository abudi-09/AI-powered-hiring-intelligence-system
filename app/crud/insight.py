from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.insight import Insight
from app.services.insight_engine import InsightEngine


async def create_insight(
    db: AsyncSession,
    entity_type: str,
    entity_id: uuid.UUID,
    insight_type: str,
    title: str,
    description: str,
    severity: str,
    confidence_score: float,
    data: dict | None = None,
) -> Insight:
    """Create a new insight."""
    insight = Insight(
        entity_type=entity_type,
        entity_id=entity_id,
        insight_type=insight_type,
        title=title,
        description=description,
        severity=severity,
        confidence_score=confidence_score,
        data=data or {},
    )
    db.add(insight)
    await db.commit()
    await db.refresh(insight)
    return insight


async def list_insights_by_entity(
    db: AsyncSession, entity_type: str, entity_id: uuid.UUID
) -> Sequence[Insight]:
    """List all insights for an entity."""
    result = await db.execute(
        select(Insight)
        .where(Insight.entity_type == entity_type, Insight.entity_id == entity_id)
        .order_by(Insight.created_at.desc())
    )
    return result.scalars().all()


async def delete_insight(db: AsyncSession, insight_id: uuid.UUID) -> bool:
    """Delete an insight by ID."""
    result = await db.execute(delete(Insight).where(Insight.id == insight_id))
    await db.commit()
    return result.rowcount > 0


async def auto_generate_insights_for_job(
    db: AsyncSession, job_id: uuid.UUID
) -> Sequence[Insight]:
    """Auto-generate and persist insights for a job."""
    engine = InsightEngine(db)
    insight_data_list = await engine.generate_job_insights(job_id)

    insights = []
    for data in insight_data_list:
        insight = await create_insight(
            db=db,
            entity_type=data["entity_type"],
            entity_id=data["entity_id"],
            insight_type=data["insight_type"],
            title=data["title"],
            description=data["description"],
            severity=data["severity"],
            confidence_score=data["confidence_score"],
            data=data.get("data"),
        )
        insights.append(insight)

    return insights


async def auto_generate_insights_for_candidate(
    db: AsyncSession, candidate_id: uuid.UUID
) -> Sequence[Insight]:
    """Auto-generate and persist insights for a candidate."""
    engine = InsightEngine(db)
    insight_data_list = await engine.generate_candidate_insights(candidate_id)

    insights = []
    for data in insight_data_list:
        insight = await create_insight(
            db=db,
            entity_type=data["entity_type"],
            entity_id=data["entity_id"],
            insight_type=data["insight_type"],
            title=data["title"],
            description=data["description"],
            severity=data["severity"],
            confidence_score=data["confidence_score"],
            data=data.get("data"),
        )
        insights.append(insight)

    return insights
