import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.services.analytics_engine import AnalyticsEngine
from app.services.insight_engine import InsightEngine


@pytest.fixture
def job_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def candidate_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.mark.asyncio
async def test_generate_job_insights_returns_empty_when_analytics_missing(
    job_id: uuid.UUID,
) -> None:
    with patch.object(
        AnalyticsEngine,
        "compute_job_analytics",
        new_callable=AsyncMock,
        return_value=None,
    ):
        engine = InsightEngine(db=AsyncMock())
        assert await engine.generate_job_insights(job_id) == []


@pytest.mark.asyncio
async def test_generate_job_insights_flags_high_hiring_difficulty(
    job_id: uuid.UUID,
) -> None:
    analytics = {
        "hiring_difficulty_score": 82.0,
        "average_match_score": 48.0,
        "candidate_count": 1,
        "top_candidate_score": None,
    }

    with patch.object(
        AnalyticsEngine,
        "compute_job_analytics",
        new_callable=AsyncMock,
        return_value=analytics,
    ):
        with patch.object(
            AnalyticsEngine,
            "compute_skill_demand",
            new_callable=AsyncMock,
            return_value=[],
        ):
            engine = InsightEngine(db=AsyncMock())
            insights = await engine.generate_job_insights(job_id)

    types = {item["insight_type"] for item in insights}
    assert "hiring_risk" in types
    assert any(item["severity"] == "high" for item in insights)
    assert any(item["title"] == "High Hiring Difficulty Detected" for item in insights)


@pytest.mark.asyncio
async def test_generate_job_insights_recommends_top_candidates(
    job_id: uuid.UUID,
) -> None:
    analytics = {
        "hiring_difficulty_score": 30.0,
        "average_match_score": 82.0,
        "candidate_count": 4,
        "top_candidate_score": 88.0,
    }
    top_candidates = [
        SimpleNamespace(candidate_id=uuid.uuid4(), score=88.0),
        SimpleNamespace(candidate_id=uuid.uuid4(), score=84.0),
    ]

    with patch.object(
        AnalyticsEngine,
        "compute_job_analytics",
        new_callable=AsyncMock,
        return_value=analytics,
    ):
        with patch.object(
            AnalyticsEngine,
            "compute_skill_demand",
            new_callable=AsyncMock,
            return_value=[],
        ):
            with patch(
                "app.services.insight_engine.get_top_candidates",
                new_callable=AsyncMock,
                return_value=top_candidates,
            ):
                engine = InsightEngine(db=AsyncMock())
                insights = await engine.generate_job_insights(job_id)

    recommendation = next(item for item in insights if item["insight_type"] == "recommendation")
    assert recommendation["data"]["top_candidate_count"] == 2


@pytest.mark.asyncio
async def test_generate_candidate_insights_highlights_strength_and_gaps(
    candidate_id: uuid.UUID,
) -> None:
    analytics = {
        "best_job_score": 90.0,
        "average_score": 72.0,
        "skill_gap_count": 6,
        "versatility_score": 6,
        "matched_job_count": 8,
    }

    with patch.object(
        AnalyticsEngine,
        "compute_candidate_analytics",
        new_callable=AsyncMock,
        return_value=analytics,
    ):
        engine = InsightEngine(db=AsyncMock())
        insights = await engine.generate_candidate_insights(candidate_id)

    types = {item["insight_type"] for item in insights}
    assert "candidate_strength" in types
    assert "skill_gap" in types
    assert any(item["severity"] == "high" for item in insights if item["insight_type"] == "skill_gap")


@pytest.mark.asyncio
async def test_generate_candidate_insights_returns_empty_when_analytics_missing(
    candidate_id: uuid.UUID,
) -> None:
    with patch.object(
        AnalyticsEngine,
        "compute_candidate_analytics",
        new_callable=AsyncMock,
        return_value=None,
    ):
        engine = InsightEngine(db=AsyncMock())
        assert await engine.generate_candidate_insights(candidate_id) == []
