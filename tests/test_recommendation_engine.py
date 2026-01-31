import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.services.analytics_engine import AnalyticsEngine
from app.services.insight_engine import InsightEngine
from app.services.recommendation_engine import RecommendationEngine


@pytest.fixture
def job_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def candidate_id() -> uuid.UUID:
    return uuid.uuid4()


def test_job_confidence_penalizes_skill_gaps() -> None:
    engine = RecommendationEngine(db=AsyncMock())
    high_gap = engine._calculate_confidence(88.0, skill_gap_penalty=12.0, difficulty_penalty=0.0)
    low_gap = engine._calculate_confidence(88.0, skill_gap_penalty=2.0, difficulty_penalty=0.0)
    assert high_gap < low_gap
    assert high_gap >= 50.0


def test_candidate_confidence_rewards_versatility_and_strength() -> None:
    engine = RecommendationEngine(db=AsyncMock())
    base = engine._calculate_candidate_confidence(72.0, versatility_score=2, has_strength=False)
    boosted = engine._calculate_candidate_confidence(72.0, versatility_score=6, has_strength=True)
    assert boosted > base


@pytest.mark.asyncio
async def test_generate_job_recommendations_ranks_by_adjusted_score(job_id: uuid.UUID) -> None:
    better_candidate = uuid.uuid4()
    weaker_candidate = uuid.uuid4()
    matches = [
        SimpleNamespace(candidate_id=better_candidate, score=90.0),
        SimpleNamespace(candidate_id=weaker_candidate, score=85.0),
    ]

    with patch(
        "app.services.recommendation_engine.get_matches_by_job",
        new_callable=AsyncMock,
        return_value=matches,
    ):
        with patch.object(
            AnalyticsEngine,
            "compute_job_analytics",
            new_callable=AsyncMock,
            return_value={"hiring_difficulty_score": 55.0},
        ):
            with patch.object(
                AnalyticsEngine,
                "compute_candidate_analytics",
                new_callable=AsyncMock,
                side_effect=[
                    {"skill_gap_count": 0},
                    {"skill_gap_count": 4},
                ],
            ):
                engine = RecommendationEngine(db=AsyncMock())
                recommendations = await engine.generate_job_recommendations(job_id, limit=2)

    assert len(recommendations) == 2
    assert recommendations[0]["recommended_entity_id"] == better_candidate
    assert recommendations[0]["rank"] == 1
    assert recommendations[0]["score"] >= recommendations[1]["score"]


@pytest.mark.asyncio
async def test_generate_job_recommendations_empty_when_no_matches(job_id: uuid.UUID) -> None:
    with patch(
        "app.services.recommendation_engine.get_matches_by_job",
        new_callable=AsyncMock,
        return_value=[],
    ):
        engine = RecommendationEngine(db=AsyncMock())
        assert await engine.generate_job_recommendations(job_id) == []


@pytest.mark.asyncio
async def test_generate_candidate_recommendations_applies_strength_bonus(
    candidate_id: uuid.UUID,
) -> None:
    job_id = uuid.uuid4()
    matches = [SimpleNamespace(job_id=job_id, score=70.0)]

    with patch(
        "app.services.recommendation_engine.get_matches_by_candidate",
        new_callable=AsyncMock,
        return_value=matches,
    ):
        with patch.object(
            AnalyticsEngine,
            "compute_candidate_analytics",
            new_callable=AsyncMock,
            return_value={"versatility_score": 4},
        ):
            with patch.object(
                InsightEngine,
                "generate_candidate_insights",
                new_callable=AsyncMock,
                return_value=[{"insight_type": "candidate_strength"}],
            ):
                engine = RecommendationEngine(db=AsyncMock())
                recommendations = await engine.generate_candidate_recommendations(
                    candidate_id,
                    limit=1,
                )

    assert len(recommendations) == 1
    assert recommendations[0]["explanation"]["strength_bonus"] == 5.0
    assert recommendations[0]["score"] > 70.0
