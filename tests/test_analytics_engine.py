import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.services.analytics_engine import AnalyticsEngine
from tests.helpers.mock_db import all_result, mock_async_session, one_result, scalar_result


@pytest.fixture
def job_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def candidate_id() -> uuid.UUID:
    return uuid.uuid4()


def test_calculate_hiring_difficulty_with_empty_pool() -> None:
    engine = AnalyticsEngine(db=AsyncMock())
    assert engine._calculate_hiring_difficulty(0.0, 1.0, 0) == 100.0


def test_calculate_hiring_difficulty_balanced_market() -> None:
    engine = AnalyticsEngine(db=AsyncMock())
    difficulty = engine._calculate_hiring_difficulty(
        avg_score=75.0,
        skill_scarcity=1.5,
        candidate_count=12,
    )
    assert 0.0 <= difficulty <= 100.0
    assert difficulty < engine._calculate_hiring_difficulty(40.0, 3.0, 2)


def test_get_bucket_label_boundaries() -> None:
    engine = AnalyticsEngine(db=AsyncMock())
    assert engine._get_bucket_label(10) == "0-20"
    assert engine._get_bucket_label(55) == "41-60"
    assert engine._get_bucket_label(95) == "81-100"


@pytest.mark.asyncio
async def test_compute_job_analytics_returns_none_for_missing_job(job_id: uuid.UUID) -> None:
    db = mock_async_session([one_result(None)])
    engine = AnalyticsEngine(db=db)
    assert await engine.compute_job_analytics(job_id) is None


@pytest.mark.asyncio
async def test_compute_job_analytics_builds_summary(job_id: uuid.UUID) -> None:
    db = mock_async_session(
        [
            one_result(("Backend Engineer",)),
            one_result((72.5, 4, 91.0)),
            scalar_result(3),
            all_result([(uuid.uuid4(),)]),
            scalar_result(5),
            scalar_result(2),
        ]
    )
    engine = AnalyticsEngine(db=db)
    result = await engine.compute_job_analytics(job_id)

    assert result is not None
    assert result["job_title"] == "Backend Engineer"
    assert result["average_match_score"] == 72.5
    assert result["candidate_count"] == 4
    assert result["skill_count"] == 3
    assert 0.0 <= result["hiring_difficulty_score"] <= 100.0


@pytest.mark.asyncio
async def test_compute_candidate_analytics_includes_skill_gap(
    candidate_id: uuid.UUID,
) -> None:
    job_a = uuid.uuid4()
    job_b = uuid.uuid4()
    owned_skill = uuid.uuid4()
    missing_skill = uuid.uuid4()

    db = mock_async_session(
        [
            one_result(("Jane Doe",)),
            one_result((88.0, 70.0, 2)),
            scalar_result(1),
            all_result([(job_a,), (job_b,)]),
            all_result([(owned_skill,)]),
            all_result([(owned_skill,), (missing_skill,)]),
        ]
    )
    engine = AnalyticsEngine(db=db)
    result = await engine.compute_candidate_analytics(candidate_id)

    assert result is not None
    assert result["candidate_name"] == "Jane Doe"
    assert result["skill_gap_count"] == 1
    assert result["matched_job_count"] == 2


@pytest.mark.asyncio
async def test_compute_match_distribution_buckets() -> None:
    db = mock_async_session([all_result([(15.0,), (35.0,), (55.0,), (75.0,), (95.0,)])])
    engine = AnalyticsEngine(db=db)
    result = await engine.compute_match_distribution()

    assert result["total_matches"] == 5
    assert result["average_score"] == 55.0
    assert sum(bucket["count"] for bucket in result["buckets"]) == 5
