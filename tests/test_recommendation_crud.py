import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.crud.recommendation import (
    create_recommendation,
    delete_recommendation,
    generate_recommendations_for_candidate,
    generate_recommendations_for_job,
    list_recommendations,
)
from app.models.recommendation import Recommendation


def _recommendation_payload(
    *,
    entity_type: str,
    entity_id: uuid.UUID,
    recommended_entity_id: uuid.UUID,
    rank: int,
) -> dict:
    return {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "recommended_entity_id": recommended_entity_id,
        "recommendation_type": "candidate_match" if entity_type == "job" else "job_match",
        "rank": rank,
        "score": 88.0 - rank,
        "confidence": 80.0,
        "explanation": {"summary": "Strong overlap"},
    }


def _recommendation_from_payload(payload: dict) -> Recommendation:
    return Recommendation(
        id=uuid.uuid4(),
        entity_type=payload["entity_type"],
        entity_id=payload["entity_id"],
        recommended_entity_id=payload["recommended_entity_id"],
        recommendation_type=payload["recommendation_type"],
        rank=payload["rank"],
        score=payload["score"],
        confidence=payload["confidence"],
        explanation=payload["explanation"],
        created_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_generate_recommendations_for_job_persists_engine_output() -> None:
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(rowcount=1))
    mock_db.commit = AsyncMock()

    job_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    payload = _recommendation_payload(
        entity_type="job",
        entity_id=job_id,
        recommended_entity_id=candidate_id,
        rank=1,
    )

    with patch(
        "app.crud.recommendation.RecommendationEngine",
    ) as engine_cls:
        engine = engine_cls.return_value
        engine.generate_job_recommendations = AsyncMock(return_value=[payload])
        with patch(
            "app.crud.recommendation.create_recommendation",
            new_callable=AsyncMock,
            side_effect=lambda **kwargs: _recommendation_from_payload(payload),
        ) as create_rec:
            results = await generate_recommendations_for_job(mock_db, job_id, limit=5)

    assert len(results) == 1
    assert results[0].entity_id == job_id
    engine.generate_job_recommendations.assert_awaited_once_with(job_id, 5)
    create_rec.assert_awaited_once()
    assert mock_db.execute.await_count == 1
    assert mock_db.commit.await_count >= 1


@pytest.mark.asyncio
async def test_generate_recommendations_for_candidate_persists_engine_output() -> None:
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(rowcount=1))
    mock_db.commit = AsyncMock()

    candidate_id = uuid.uuid4()
    job_id = uuid.uuid4()
    payload = _recommendation_payload(
        entity_type="candidate",
        entity_id=candidate_id,
        recommended_entity_id=job_id,
        rank=1,
    )

    with patch(
        "app.crud.recommendation.RecommendationEngine",
    ) as engine_cls:
        engine = engine_cls.return_value
        engine.generate_candidate_recommendations = AsyncMock(return_value=[payload])
        with patch(
            "app.crud.recommendation.create_recommendation",
            new_callable=AsyncMock,
            side_effect=lambda **kwargs: _recommendation_from_payload(payload),
        ) as create_rec:
            results = await generate_recommendations_for_candidate(mock_db, candidate_id, limit=3)

    assert len(results) == 1
    assert results[0].entity_id == candidate_id
    engine.generate_candidate_recommendations.assert_awaited_once_with(candidate_id, 3)
    create_rec.assert_awaited_once()
    assert mock_db.execute.await_count == 1
    assert mock_db.commit.await_count >= 1


@pytest.mark.asyncio
async def test_list_recommendations_returns_ranked_rows() -> None:
    mock_db = AsyncMock()
    job_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    recommendation = _recommendation_from_payload(
        _recommendation_payload(
            entity_type="job",
            entity_id=job_id,
            recommended_entity_id=candidate_id,
            rank=1,
        )
    )
    result = MagicMock()
    result.scalars.return_value.all.return_value = [recommendation]
    mock_db.execute = AsyncMock(return_value=result)

    rows = await list_recommendations(mock_db, "job", job_id)

    assert len(rows) == 1
    assert rows[0].rank == 1


@pytest.mark.asyncio
async def test_delete_recommendation_returns_true_when_row_removed() -> None:
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(rowcount=1))
    mock_db.commit = AsyncMock()

    deleted = await delete_recommendation(mock_db, uuid.uuid4())

    assert deleted is True
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_recommendation_persists_row() -> None:
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    job_id = uuid.uuid4()
    candidate_id = uuid.uuid4()

    with patch(
        "app.crud.recommendation.Recommendation",
        side_effect=lambda **kwargs: Recommendation(
            id=uuid.uuid4(),
            created_at=datetime.now(timezone.utc),
            **kwargs,
        ),
    ):
        recommendation = await create_recommendation(
            mock_db,
            entity_type="job",
            entity_id=job_id,
            recommended_entity_id=candidate_id,
            recommendation_type="candidate_match",
            rank=1,
            score=90.0,
            confidence=85.0,
            explanation={"summary": "Strong overlap"},
        )

    assert recommendation.entity_id == job_id
    mock_db.add.assert_called_once()
    mock_db.commit.assert_awaited_once()
    mock_db.refresh.assert_awaited_once()
