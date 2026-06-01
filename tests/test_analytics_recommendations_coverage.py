import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token, get_password_hash
from app.db.session import get_db
from app.main import create_app
from app.models.match import MatchScore
from app.models.recommendation import Recommendation
from app.models.user import User, UserRole
from app.services.analytics_engine import AnalyticsEngine
from app.services.insight_engine import InsightEngine
from app.services.recommendation_engine import RecommendationEngine
from tests.helpers.mock_db import all_result, mock_async_session, one_result, scalar_result


@pytest.mark.asyncio
async def test_compute_skill_demand_and_scarcity() -> None:
    skill_id = uuid.uuid4()
    responses = [
        all_result([(skill_id, "Python", 4)]),
        all_result([(skill_id, 2)]),
        all_result([(skill_id, "Python", 4)]),
        all_result([(skill_id, 2)]),
    ]
    db = mock_async_session(responses)
    engine = AnalyticsEngine(db=db)
    demand = await engine.compute_skill_demand()
    assert demand[0]["scarcity_ratio"] == 2.0

    scarce = await engine.compute_skill_scarcity()
    assert scarce[0]["skill_name"] == "Python"

    empty_db = mock_async_session([all_result([])])
    empty_engine = AnalyticsEngine(db=empty_db)
    distribution = await empty_engine.compute_match_distribution()
    assert distribution["total_matches"] == 0
    assert distribution["median_bucket"] == "No data"


@pytest.mark.asyncio
async def test_recommendation_engine_job_and_candidate_paths() -> None:
    job_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    match = MatchScore(
        id=uuid.uuid4(),
        candidate_id=candidate_id,
        job_id=job_id,
        score=88.0,
        explanation={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    mock_db = AsyncMock()

    with patch(
        "app.services.recommendation_engine.get_matches_by_job",
        new_callable=AsyncMock,
        return_value=[match],
    ):
        engine = RecommendationEngine(mock_db)
        engine.analytics.compute_job_analytics = AsyncMock(
            return_value={"hiring_difficulty_score": 80.0}
        )
        engine.analytics.compute_candidate_analytics = AsyncMock(
            return_value={"skill_gap_count": 3, "versatility_score": 4}
        )
        engine.insight_engine.generate_candidate_insights = AsyncMock(return_value=[])

        job_recs = await engine.generate_job_recommendations(job_id, limit=5)
        assert job_recs[0]["rank"] == 1
        assert job_recs[0]["score"] <= 100.0

    with patch(
        "app.services.recommendation_engine.get_matches_by_candidate",
        new_callable=AsyncMock,
        return_value=[match],
    ):
        engine = RecommendationEngine(mock_db)
        engine.analytics.compute_candidate_analytics = AsyncMock(
            return_value={"versatility_score": 6}
        )
        engine.insight_engine.generate_candidate_insights = AsyncMock(
            return_value=[{"insight_type": "candidate_strength"}]
        )
        candidate_recs = await engine.generate_candidate_recommendations(candidate_id, limit=3)
        assert candidate_recs[0]["confidence"] >= 50.0

    empty_engine = RecommendationEngine(mock_db)
    with patch(
        "app.services.recommendation_engine.get_matches_by_candidate",
        new_callable=AsyncMock,
        return_value=[],
    ):
        assert await empty_engine.generate_candidate_recommendations(candidate_id) == []


def test_recommendation_confidence_branches() -> None:
    engine = RecommendationEngine(AsyncMock())
    assert engine._calculate_confidence(90.0, 12.0, 8.0) == 80.0
    assert engine._calculate_confidence(65.0, 3.0, 2.0) == 75.0
    assert engine._calculate_candidate_confidence(55.0, 6, True) >= 70.0


@pytest.fixture
def recruiter_user() -> User:
    now = datetime.now(timezone.utc)
    return User(
        id=uuid.UUID("00000000-0000-4000-8000-000000000020"),
        email="recruiter@example.com",
        hashed_password=get_password_hash("Password123"),
        full_name="Recruiter User",
        role=UserRole.Recruiter,
        is_active=True,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_recommendations_candidate_list_and_delete_404(recruiter_user: User) -> None:
    candidate_id = uuid.uuid4()
    recommendation = Recommendation(
        id=uuid.uuid4(),
        entity_type="candidate",
        entity_id=candidate_id,
        recommended_entity_id=uuid.uuid4(),
        recommendation_type="job_match",
        rank=1,
        score=80.0,
        confidence=75.0,
        explanation={},
        created_at=datetime.now(timezone.utc),
    )
    mock_session = AsyncMock()
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = recruiter_user
    mock_session.execute = AsyncMock(return_value=user_result)

    app = create_app()

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db
    token = create_access_token(subject=str(recruiter_user.id), role=recruiter_user.role.value)

    with patch(
        "app.api.recommendations.recommendation_crud.list_recommendations",
        new_callable=AsyncMock,
        return_value=[recommendation],
    ), patch(
        "app.api.recommendations.recommendation_crud.delete_recommendation",
        new_callable=AsyncMock,
        return_value=False,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            list_response = await client.get(
                f"/recommendations/candidate/{candidate_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            delete_response = await client.delete(
                f"/recommendations/{uuid.uuid4()}",
                headers={"Authorization": f"Bearer {token}"},
            )

    app.dependency_overrides.clear()
    assert list_response.status_code == 200
    assert delete_response.status_code == 404
