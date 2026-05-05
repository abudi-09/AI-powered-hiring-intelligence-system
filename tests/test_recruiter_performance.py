import uuid

import pytest

from app.services.intelligence_engine import IntelligenceEngine
from tests.helpers.mock_db import all_result, mock_async_session, scalar_result


@pytest.fixture
def recruiter_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.mark.asyncio
async def test_calculate_recruiter_performance_aggregates_job_metrics(
    recruiter_id: uuid.UUID,
) -> None:
    job_a = uuid.uuid4()
    job_b = uuid.uuid4()
    db = mock_async_session(
        [
            scalar_result(2),
            all_result([(job_a,), (job_b,)]),
            scalar_result(3),
            all_result([(85.0,), (72.0,), (55.0,)]),
            all_result([(job_a, 80.0), (job_b, 60.0)]),
        ]
    )

    result = await IntelligenceEngine.calculate_recruiter_performance(db, recruiter_id)

    assert result["recommendation_acceptance_rate"] == pytest.approx(50.0)
    assert result["avg_time_to_hire"] == pytest.approx(33.5)
    assert result["hire_success_rate"] == pytest.approx(63.6, abs=0.1)
    assert result["breakdown"]["total_jobs_posted"] == 2
    assert result["breakdown"]["total_recommendations_made"] == 3
    assert result["breakdown"]["high_quality_recommendations"] == 1


@pytest.mark.asyncio
async def test_calculate_recruiter_performance_returns_zeros_without_jobs(
    recruiter_id: uuid.UUID,
) -> None:
    db = mock_async_session(
        [
            scalar_result(0),
            all_result([]),
        ]
    )

    result = await IntelligenceEngine.calculate_recruiter_performance(db, recruiter_id)

    assert result["recommendation_acceptance_rate"] == 0.0
    assert result["avg_time_to_hire"] == 0.0
    assert result["hire_success_rate"] == 0.0
    assert result["breakdown"]["total_jobs_posted"] == 0
