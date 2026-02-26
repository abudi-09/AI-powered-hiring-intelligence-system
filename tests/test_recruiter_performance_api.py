import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token, get_password_hash
from app.db.session import get_db
from app.main import create_app
from app.models.intelligence import RecruiterPerformance
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
def recruiter_id(recruiter_user: User) -> uuid.UUID:
    return recruiter_user.id


@pytest.fixture
async def intelligence_client(recruiter_user: User):
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
        yield client, token, mock_session

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_recruiter_performance_returns_404_before_generation(
    intelligence_client,
    recruiter_id: uuid.UUID,
) -> None:
    client, token, _ = intelligence_client

    with patch(
        "app.api.intelligence.intelligence_crud.get_recruiter_performance",
        new_callable=AsyncMock,
        return_value=None,
    ):
        response = await client.get(
            f"/intelligence/recruiter/{recruiter_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_generate_recruiter_performance_returns_metrics(
    intelligence_client,
    recruiter_id: uuid.UUID,
) -> None:
    client, token, _ = intelligence_client
    performance = RecruiterPerformance(
        id=uuid.uuid4(),
        recruiter_id=recruiter_id,
        recommendation_acceptance_rate=68.5,
        avg_time_to_hire=29.0,
        hire_success_rate=74.0,
        breakdown={"total_jobs_posted": 4},
        created_at=datetime.now(timezone.utc),
    )

    with patch(
        "app.api.intelligence.intelligence_crud.generate_recruiter_performance",
        new_callable=AsyncMock,
        return_value=performance,
    ):
        response = await client.post(
            f"/intelligence/generate/recruiter/{recruiter_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 201
    body = response.json()
    assert body["recruiter_id"] == str(recruiter_id)
    assert body["recommendation_acceptance_rate"] == pytest.approx(68.5)
    assert body["breakdown"]["total_jobs_posted"] == 4
