import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.crud.intelligence import (
    generate_candidate_intelligence,
    generate_job_intelligence,
    generate_match_intelligence,
    generate_recruiter_performance,
    generate_skill_intelligence,
    get_candidate_intelligence,
    get_job_intelligence,
    get_match_intelligence,
    get_recruiter_performance,
    get_skill_intelligence,
)
from app.models.intelligence import (
    CandidateIntelligence,
    JobIntelligence,
    MatchIntelligence,
    RecruiterPerformance,
    SkillIntelligence,
)
from app.models.user import User, UserRole


def _mock_db_with_refresh(record) -> AsyncMock:
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(rowcount=1))
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock(side_effect=lambda obj: setattr(obj, "id", uuid.uuid4()) or setattr(
        obj, "created_at", datetime.now(timezone.utc)
    ))
    mock_db.add = MagicMock()
    return mock_db


@pytest.mark.asyncio
async def test_generate_job_intelligence_persists_metrics() -> None:
    job_id = uuid.uuid4()
    mock_db = _mock_db_with_refresh(None)
    metrics = {
        "hiring_difficulty_score": 72.0,
        "candidate_availability_ratio": 0.4,
        "skill_scarcity_index": 1.8,
        "avg_match_score": 65.0,
        "breakdown": {"top_gap": "Python"},
    }

    with patch(
        "app.crud.intelligence.IntelligenceEngine.calculate_job_intelligence",
        new_callable=AsyncMock,
        return_value=metrics,
    ):
        result = await generate_job_intelligence(mock_db, job_id)

    assert isinstance(result, JobIntelligence)
    assert result.job_id == job_id
    assert result.hiring_difficulty_score == 72.0
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_job_intelligence_returns_latest_row() -> None:
    job_id = uuid.uuid4()
    row = JobIntelligence(
        id=uuid.uuid4(),
        job_id=job_id,
        hiring_difficulty_score=50.0,
        candidate_availability_ratio=0.5,
        skill_scarcity_index=1.0,
        avg_match_score=60.0,
        breakdown={},
        created_at=datetime.now(timezone.utc),
    )
    mock_db = AsyncMock()
    lookup = MagicMock()
    lookup.scalar_one_or_none.return_value = row
    mock_db.execute = AsyncMock(return_value=lookup)

    result = await get_job_intelligence(mock_db, job_id)

    assert result is row


@pytest.mark.asyncio
async def test_generate_candidate_intelligence_persists_metrics() -> None:
    candidate_id = uuid.uuid4()
    mock_db = _mock_db_with_refresh(None)
    metrics = {
        "market_competitiveness_score": 80.0,
        "versatility_index": 0.7,
        "skill_depth_score": 75.0,
        "growth_potential_score": 68.0,
        "breakdown": {},
    }

    with patch(
        "app.crud.intelligence.IntelligenceEngine.calculate_candidate_intelligence",
        new_callable=AsyncMock,
        return_value=metrics,
    ):
        result = await generate_candidate_intelligence(mock_db, candidate_id)

    assert isinstance(result, CandidateIntelligence)
    assert result.candidate_id == candidate_id
    assert result.market_competitiveness_score == 80.0


@pytest.mark.asyncio
async def test_get_candidate_intelligence_returns_row() -> None:
    candidate_id = uuid.uuid4()
    row = CandidateIntelligence(
        id=uuid.uuid4(),
        candidate_id=candidate_id,
        market_competitiveness_score=70.0,
        versatility_index=0.6,
        skill_depth_score=65.0,
        growth_potential_score=60.0,
        breakdown={},
        created_at=datetime.now(timezone.utc),
    )
    mock_db = AsyncMock()
    lookup = MagicMock()
    lookup.scalar_one_or_none.return_value = row
    mock_db.execute = AsyncMock(return_value=lookup)

    result = await get_candidate_intelligence(mock_db, candidate_id)

    assert result is row


@pytest.mark.asyncio
async def test_generate_skill_intelligence_persists_metrics() -> None:
    skill_id = uuid.uuid4()
    mock_db = _mock_db_with_refresh(None)
    metrics = {
        "demand_count": 5,
        "supply_count": 2,
        "scarcity_ratio": 2.5,
        "avg_required_level": 3.0,
        "breakdown": {},
    }

    with patch(
        "app.crud.intelligence.IntelligenceEngine.calculate_skill_intelligence",
        new_callable=AsyncMock,
        return_value=metrics,
    ):
        result = await generate_skill_intelligence(mock_db, skill_id)

    assert isinstance(result, SkillIntelligence)
    assert result.skill_id == skill_id
    assert result.demand_count == 5


@pytest.mark.asyncio
async def test_get_skill_intelligence_returns_row() -> None:
    skill_id = uuid.uuid4()
    row = SkillIntelligence(
        id=uuid.uuid4(),
        skill_id=skill_id,
        demand_count=4,
        supply_count=2,
        scarcity_ratio=2.0,
        avg_required_level=2.5,
        breakdown={},
        created_at=datetime.now(timezone.utc),
    )
    mock_db = AsyncMock()
    lookup = MagicMock()
    lookup.scalar_one_or_none.return_value = row
    mock_db.execute = AsyncMock(return_value=lookup)

    result = await get_skill_intelligence(mock_db, skill_id)

    assert result is row


@pytest.mark.asyncio
async def test_generate_match_intelligence_persists_metrics() -> None:
    mock_db = _mock_db_with_refresh(None)
    metrics = {
        "score_distribution": {"high": 10, "medium": 20, "low": 5},
        "top_percentile_score": 92.0,
        "low_match_ratio": 0.15,
        "recommendation_quality_index": 0.78,
    }

    with patch(
        "app.crud.intelligence.IntelligenceEngine.calculate_match_intelligence",
        new_callable=AsyncMock,
        return_value=metrics,
    ):
        result = await generate_match_intelligence(mock_db)

    assert isinstance(result, MatchIntelligence)
    assert result.top_percentile_score == 92.0


@pytest.mark.asyncio
async def test_get_match_intelligence_returns_row() -> None:
    row = MatchIntelligence(
        id=uuid.uuid4(),
        score_distribution={"high": 1},
        top_percentile_score=90.0,
        low_match_ratio=0.1,
        recommendation_quality_index=0.8,
        created_at=datetime.now(timezone.utc),
    )
    mock_db = AsyncMock()
    lookup = MagicMock()
    lookup.scalar_one_or_none.return_value = row
    mock_db.execute = AsyncMock(return_value=lookup)

    result = await get_match_intelligence(mock_db)

    assert result is row


@pytest.mark.asyncio
async def test_generate_recruiter_performance_persists_metrics() -> None:
    recruiter_id = uuid.uuid4()
    user = User(
        id=recruiter_id,
        full_name="Recruiter",
        email="recruiter@example.com",
        hashed_password="hashed",
        role=UserRole.Recruiter,
        is_active=True,
    )
    mock_db = _mock_db_with_refresh(None)
    lookup = MagicMock()
    lookup.scalar_one_or_none.return_value = user
    mock_db.execute = AsyncMock(return_value=lookup)
    metrics = {
        "recommendation_acceptance_rate": 0.55,
        "avg_time_to_hire": 21.0,
        "hire_success_rate": 0.42,
        "breakdown": {},
    }

    with patch(
        "app.crud.intelligence.IntelligenceEngine.calculate_recruiter_performance",
        new_callable=AsyncMock,
        return_value=metrics,
    ):
        result = await generate_recruiter_performance(mock_db, recruiter_id)

    assert isinstance(result, RecruiterPerformance)
    assert result.recruiter_id == recruiter_id
    assert result.hire_success_rate == 0.42


@pytest.mark.asyncio
async def test_get_recruiter_performance_returns_row() -> None:
    recruiter_id = uuid.uuid4()
    row = RecruiterPerformance(
        id=uuid.uuid4(),
        recruiter_id=recruiter_id,
        recommendation_acceptance_rate=0.5,
        avg_time_to_hire=18.0,
        hire_success_rate=0.4,
        breakdown={},
        created_at=datetime.now(timezone.utc),
    )
    mock_db = AsyncMock()
    lookup = MagicMock()
    lookup.scalar_one_or_none.return_value = row
    mock_db.execute = AsyncMock(return_value=lookup)

    result = await get_recruiter_performance(mock_db, recruiter_id)

    assert result is row
