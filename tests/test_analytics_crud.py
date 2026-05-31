import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.crud.analytics import (
    get_candidate_analytics,
    get_job_analytics,
    get_match_distribution,
    get_skill_demand,
    get_skill_scarcity,
)


@pytest.mark.asyncio
async def test_get_job_analytics_returns_payload() -> None:
    mock_db = AsyncMock()
    job_id = uuid.uuid4()
    payload = {"job_id": str(job_id), "job_title": "Backend Engineer", "candidate_count": 3}

    with patch(
        "app.crud.analytics.AnalyticsEngine.compute_job_analytics",
        new_callable=AsyncMock,
        return_value=payload,
    ):
        result = await get_job_analytics(mock_db, job_id)

    assert result["job_title"] == "Backend Engineer"


@pytest.mark.asyncio
async def test_get_job_analytics_raises_404_when_missing() -> None:
    mock_db = AsyncMock()

    with patch(
        "app.crud.analytics.AnalyticsEngine.compute_job_analytics",
        new_callable=AsyncMock,
        return_value=None,
    ):
        with pytest.raises(HTTPException) as exc:
            await get_job_analytics(mock_db, uuid.uuid4())

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_candidate_analytics_raises_404_when_missing() -> None:
    mock_db = AsyncMock()

    with patch(
        "app.crud.analytics.AnalyticsEngine.compute_candidate_analytics",
        new_callable=AsyncMock,
        return_value=None,
    ):
        with pytest.raises(HTTPException) as exc:
            await get_candidate_analytics(mock_db, uuid.uuid4())

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_skill_demand_and_scarcity_delegate_to_engine() -> None:
    mock_db = AsyncMock()
    rows = [{"skill_name": "Python", "demand_count": 4, "supply_count": 2, "scarcity_ratio": 2.0}]

    with patch(
        "app.crud.analytics.AnalyticsEngine.compute_skill_demand",
        new_callable=AsyncMock,
        return_value=rows,
    ), patch(
        "app.crud.analytics.AnalyticsEngine.compute_skill_scarcity",
        new_callable=AsyncMock,
        return_value=rows,
    ):
        demand = await get_skill_demand(mock_db)
        scarcity = await get_skill_scarcity(mock_db)

    assert demand[0]["skill_name"] == "Python"
    assert scarcity[0]["scarcity_ratio"] == 2.0


@pytest.mark.asyncio
async def test_get_match_distribution_returns_engine_payload() -> None:
    mock_db = AsyncMock()
    payload = {"total_matches": 10, "average_score": 72.0, "buckets": []}

    with patch(
        "app.crud.analytics.AnalyticsEngine.compute_match_distribution",
        new_callable=AsyncMock,
        return_value=payload,
    ):
        result = await get_match_distribution(mock_db)

    assert result["total_matches"] == 10
