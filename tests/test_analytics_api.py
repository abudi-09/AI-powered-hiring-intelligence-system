import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token, get_password_hash
from app.db.session import get_db
from app.main import create_app
from app.models.user import User, UserRole


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


@pytest.fixture
async def analytics_client(recruiter_user: User):
    mock_session = AsyncMock()
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = recruiter_user
    mock_session.execute = AsyncMock(return_value=user_result)

    app = create_app()

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db
    token = create_access_token(subject=str(recruiter_user.id), role=recruiter_user.role.value)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client, token

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_job_analytics_endpoint_returns_snapshot(analytics_client) -> None:
    client, token = analytics_client
    job_id = uuid.uuid4()
    payload = {
        "job_id": str(job_id),
        "job_title": "Backend Engineer",
        "average_match_score": 72.5,
        "candidate_count": 4,
        "hiring_difficulty_score": 61.0,
        "top_candidate_score": 88.0,
        "skill_count": 3,
    }

    with patch(
        "app.api.analytics.get_job_analytics",
        new_callable=AsyncMock,
        return_value=payload,
    ):
        response = await client.get(
            f"/analytics/jobs/{job_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["job_title"] == "Backend Engineer"
    assert body["candidate_count"] == 4


@pytest.mark.asyncio
async def test_skill_demand_endpoint_returns_catalog(analytics_client) -> None:
    client, token = analytics_client
    skill_id = uuid.uuid4()
    rows = [
        {
            "skill_id": str(skill_id),
            "skill_name": "Python",
            "demand_count": 5,
            "supply_count": 2,
            "scarcity_ratio": 2.5,
        }
    ]

    with patch(
        "app.api.analytics.get_skill_demand",
        new_callable=AsyncMock,
        return_value=rows,
    ):
        response = await client.get(
            "/analytics/skills/demand",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    assert response.json()[0]["skill_name"] == "Python"


@pytest.mark.asyncio
async def test_analytics_routes_require_authentication() -> None:
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/analytics/skills/demand")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_candidate_analytics_endpoint_returns_snapshot(analytics_client) -> None:
    client, token = analytics_client
    candidate_id = uuid.uuid4()
    payload = {
        "candidate_id": str(candidate_id),
        "candidate_name": "Jane Doe",
        "best_job_score": 88.0,
        "average_score": 72.0,
        "versatility_score": 4,
        "skill_gap_count": 2,
        "matched_job_count": 3,
    }

    with patch(
        "app.api.analytics.get_candidate_analytics",
        new_callable=AsyncMock,
        return_value=payload,
    ):
        response = await client.get(
            f"/analytics/candidates/{candidate_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    assert response.json()["candidate_name"] == "Jane Doe"


@pytest.mark.asyncio
async def test_skill_scarcity_and_match_distribution_endpoints(analytics_client) -> None:
    client, token = analytics_client
    scarcity_rows = [
        {
            "skill_id": str(uuid.uuid4()),
            "skill_name": "Rust",
            "demand_count": 6,
            "supply_count": 1,
            "scarcity_ratio": 6.0,
        }
    ]
    distribution = {
        "total_matches": 12,
        "average_score": 70.0,
        "median_bucket": "60-79",
        "buckets": [{"range_start": 60, "range_end": 79, "count": 5, "percentage": 41.7}],
    }

    with patch(
        "app.api.analytics.get_skill_scarcity",
        new_callable=AsyncMock,
        return_value=scarcity_rows,
    ), patch(
        "app.api.analytics.get_match_distribution",
        new_callable=AsyncMock,
        return_value=distribution,
    ):
        scarcity_response = await client.get(
            "/analytics/skills/scarcity",
            headers={"Authorization": f"Bearer {token}"},
        )
        distribution_response = await client.get(
            "/analytics/matches/distribution",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert scarcity_response.status_code == 200
    assert scarcity_response.json()[0]["skill_name"] == "Rust"
    assert distribution_response.status_code == 200
    assert distribution_response.json()["total_matches"] == 12
