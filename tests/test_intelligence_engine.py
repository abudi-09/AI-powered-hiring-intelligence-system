import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.intelligence_engine import IntelligenceEngine
from tests.helpers.mock_db import all_result, mock_async_session, scalar_result


@pytest.fixture
def job_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def candidate_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def skill_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.mark.asyncio
async def test_calculate_job_intelligence_combines_match_and_scarcity(job_id: uuid.UUID) -> None:
    skill_a = uuid.uuid4()
    skill_b = uuid.uuid4()
    db = mock_async_session(
        [
            scalar_result(SimpleNamespace(id=job_id)),
            scalar_result(2),
            all_result([(82.0,), (74.0,)]),
            all_result([(skill_a,), (skill_b,)]),
            all_result([(skill_a, 4), (skill_b, 3)]),
            all_result([(skill_a, 2), (skill_b, 1)]),
        ]
    )

    result = await IntelligenceEngine.calculate_job_intelligence(db, job_id)

    assert result["avg_match_score"] == 78.0
    assert result["candidate_availability_ratio"] == 1.0
    assert result["breakdown"]["required_skills_count"] == 2
    assert 0.0 <= result["hiring_difficulty_score"] <= 100.0
    assert 0.0 <= result["skill_scarcity_index"] <= 100.0


@pytest.mark.asyncio
async def test_calculate_job_intelligence_raises_for_missing_job(job_id: uuid.UUID) -> None:
    db = mock_async_session([scalar_result(None)])
    with pytest.raises(ValueError, match="not found"):
        await IntelligenceEngine.calculate_job_intelligence(db, job_id)


@pytest.mark.asyncio
async def test_calculate_candidate_intelligence_uses_skill_levels(
    candidate_id: uuid.UUID,
) -> None:
    db = mock_async_session(
        [
            scalar_result(SimpleNamespace(id=candidate_id)),
            all_result([("senior", 6.0), ("mid", 2.0)]),
            all_result([(91.0,), (84.0,), (79.0,)]),
        ]
    )

    result = await IntelligenceEngine.calculate_candidate_intelligence(db, candidate_id)

    assert result["market_competitiveness_score"] > 0.0
    assert result["versatility_index"] > 0.0
    assert result["skill_depth_score"] > 0.0
    assert result["breakdown"]["skill_count"] == 2


@pytest.mark.asyncio
async def test_calculate_skill_intelligence_reports_demand_supply(skill_id: uuid.UUID) -> None:
    db = mock_async_session(
        [
            scalar_result(8),
            scalar_result(3),
            all_result([(0.9,), (0.7,)]),
            all_result([("senior", 5.0), ("mid", 2.0)]),
        ]
    )

    result = await IntelligenceEngine.calculate_skill_intelligence(db, skill_id)

    assert result["demand_count"] == 8
    assert result["supply_count"] == 3
    assert result["scarcity_ratio"] == pytest.approx(2.67, rel=0.01)
    assert result["breakdown"]["expert_candidates"] >= 1


@pytest.mark.asyncio
async def test_calculate_match_intelligence_empty_state() -> None:
    db = mock_async_session([all_result([])])
    result = await IntelligenceEngine.calculate_match_intelligence(db)

    assert result["top_percentile_score"] == 0.0
    assert result["score_distribution"] == {}
    assert result["breakdown"] == {}


@pytest.mark.asyncio
async def test_calculate_match_intelligence_distribution() -> None:
    db = mock_async_session(
        [
            all_result([(95.0,), (72.0,), (55.0,), (30.0,)]),
            all_result([(88.0,), (76.0,)]),
        ]
    )
    result = await IntelligenceEngine.calculate_match_intelligence(db)

    assert result["breakdown"]["total_matches"] == 4
    assert result["breakdown"]["total_recommendations"] == 2
    assert sum(result["score_distribution"].values()) == 4
    assert result["recommendation_quality_index"] == 82.0
