import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token, get_password_hash
from app.db.session import get_db
from app.main import create_app
from app.models.recommendation import Recommendation
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
async def recommendations_client(recruiter_user: User):
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
async def test_get_job_recommendations_returns_list(recommendations_client) -> None:
    client, token = recommendations_client
    job_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    recommendation = Recommendation(
        id=uuid.uuid4(),
        entity_type="job",
        entity_id=job_id,
        recommended_entity_id=candidate_id,
        recommendation_type="candidate_match",
        rank=1,
        score=90.0,
        confidence=85.0,
        explanation={"summary": "Strong Python overlap"},
        created_at=datetime.now(timezone.utc),
    )

    with patch(
        "app.api.recommendations.recommendation_crud.list_recommendations",
        new_callable=AsyncMock,
        return_value=[recommendation],
    ):
        response = await client.get(
            f"/recommendations/job/{job_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["recommendations"][0]["score"] == pytest.approx(90.0)


@pytest.mark.asyncio
async def test_generate_job_recommendations_returns_created_rows(recommendations_client) -> None:
    client, token = recommendations_client
    job_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    recommendation = Recommendation(
        id=uuid.uuid4(),
        entity_type="job",
        entity_id=job_id,
        recommended_entity_id=candidate_id,
        recommendation_type="candidate_match",
        rank=1,
        score=88.0,
        confidence=80.0,
        explanation={"summary": "Good fit"},
        created_at=datetime.now(timezone.utc),
    )

    with patch(
        "app.api.recommendations.recommendation_crud.generate_recommendations_for_job",
        new_callable=AsyncMock,
        return_value=[recommendation],
    ):
        response = await client.post(
            f"/recommendations/generate/job/{job_id}?limit=5",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    assert response.json()["total"] == 1


@pytest.mark.asyncio
async def test_recommendations_routes_require_authentication() -> None:
    job_id = uuid.uuid4()
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(f"/recommendations/job/{job_id}")

    assert response.status_code == 401
