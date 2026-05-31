import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token, get_password_hash
from app.db.session import get_db
from app.main import create_app
from app.models.insight import Insight
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
async def insights_client(recruiter_user: User):
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


def _insight(*, entity_type: str, entity_id: uuid.UUID) -> Insight:
    return Insight(
        id=uuid.uuid4(),
        entity_type=entity_type,
        entity_id=entity_id,
        insight_type="skill_gap",
        title="Missing backend depth",
        description="Several required skills are underrepresented.",
        severity="medium",
        confidence_score=82.0,
        data={"missing_skills": ["Python"]},
        created_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_get_job_insights_returns_list(insights_client) -> None:
    client, token = insights_client
    job_id = uuid.uuid4()
    insight = _insight(entity_type="job", entity_id=job_id)

    with patch(
        "app.api.insights.insight_crud.list_insights_by_entity",
        new_callable=AsyncMock,
        return_value=[insight],
    ):
        response = await client.get(
            f"/insights/job/{job_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["insights"][0]["title"] == "Missing backend depth"


@pytest.mark.asyncio
async def test_get_candidate_insights_returns_list(insights_client) -> None:
    client, token = insights_client
    candidate_id = uuid.uuid4()
    insight = _insight(entity_type="candidate", entity_id=candidate_id)

    with patch(
        "app.api.insights.insight_crud.list_insights_by_entity",
        new_callable=AsyncMock,
        return_value=[insight],
    ):
        response = await client.get(
            f"/insights/candidate/{candidate_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    assert response.json()["insights"][0]["entity_type"] == "candidate"


@pytest.mark.asyncio
async def test_generate_job_insights_returns_created_rows(insights_client) -> None:
    client, token = insights_client
    job_id = uuid.uuid4()
    insight = _insight(entity_type="job", entity_id=job_id)

    with patch(
        "app.api.insights.insight_crud.auto_generate_insights_for_job",
        new_callable=AsyncMock,
        return_value=[insight],
    ):
        response = await client.post(
            f"/insights/generate/job/{job_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    assert response.json()["total"] == 1


@pytest.mark.asyncio
async def test_generate_candidate_insights_returns_created_rows(insights_client) -> None:
    client, token = insights_client
    candidate_id = uuid.uuid4()
    insight = _insight(entity_type="candidate", entity_id=candidate_id)

    with patch(
        "app.api.insights.insight_crud.auto_generate_insights_for_candidate",
        new_callable=AsyncMock,
        return_value=[insight],
    ):
        response = await client.post(
            f"/insights/generate/candidate/{candidate_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    assert response.json()["insights"][0]["severity"] == "medium"


@pytest.mark.asyncio
async def test_delete_insight_returns_success(insights_client) -> None:
    client, token = insights_client
    insight_id = uuid.uuid4()

    with patch(
        "app.api.insights.insight_crud.delete_insight",
        new_callable=AsyncMock,
        return_value=True,
    ):
        response = await client.delete(
            f"/insights/{insight_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    assert response.json()["message"] == "Insight deleted successfully"


@pytest.mark.asyncio
async def test_delete_insight_returns_404_when_missing(insights_client) -> None:
    client, token = insights_client
    insight_id = uuid.uuid4()

    with patch(
        "app.api.insights.insight_crud.delete_insight",
        new_callable=AsyncMock,
        return_value=False,
    ):
        response = await client.delete(
            f"/insights/{insight_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Insight not found"


@pytest.mark.asyncio
async def test_insights_routes_require_authentication() -> None:
    job_id = uuid.uuid4()
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(f"/insights/job/{job_id}")

    assert response.status_code == 401
