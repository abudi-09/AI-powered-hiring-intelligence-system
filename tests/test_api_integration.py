import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token, get_password_hash
from app.db.session import get_db
from app.main import create_app
from app.models.skill import Skill
from app.models.user import User, UserRole


@pytest.fixture
def active_user() -> User:
    now = datetime.now(timezone.utc)
    return User(
        id=uuid.UUID("00000000-0000-4000-8000-000000000001"),
        email="recruiter@example.com",
        hashed_password=get_password_hash("Password123"),
        full_name="Recruiter User",
        role=UserRole.Recruiter,
        is_active=True,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
async def api_client(active_user: User):
    mock_session = AsyncMock()
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = active_user
    mock_session.execute = AsyncMock(return_value=user_result)

    app = create_app()

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_openapi_document_is_available(api_client: AsyncClient) -> None:
    response = await api_client.get("/openapi.json")
    assert response.status_code == 200
    payload = response.json()
    assert payload["info"]["title"] == "AI Powered Hiring System"
    assert "/auth/login" in payload["paths"]


@pytest.mark.asyncio
async def test_login_with_json_body_returns_token(
    api_client: AsyncClient,
    active_user: User,
) -> None:
    response = await api_client.post(
        "/auth/login",
        json={"email": active_user.email, "password": "Password123"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert isinstance(body["access_token"], str)
    assert len(body["access_token"]) > 0


@pytest.mark.asyncio
async def test_login_rejects_invalid_credentials(api_client: AsyncClient) -> None:
    response = await api_client.post(
        "/auth/login",
        json={"email": "recruiter@example.com", "password": "wrong-password"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_requires_credentials(api_client: AsyncClient) -> None:
    response = await api_client.post("/auth/login", json={})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_health_endpoint_returns_ok(api_client: AsyncClient) -> None:
    response = await api_client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["app_env"] == "development"


@pytest.mark.asyncio
async def test_ready_endpoint_reports_database_status(api_client: AsyncClient) -> None:
    response = await api_client.get("/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["database"] == "connected"
    assert body["status"] == "ready"
    assert body["app_env"] == "development"


@pytest.mark.asyncio
async def test_ready_endpoint_marks_degraded_when_database_unavailable() -> None:
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(side_effect=RuntimeError("database unavailable"))

    app = create_app()

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/ready")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["database"] == "unavailable"


@pytest.mark.asyncio
async def test_users_me_requires_authentication(api_client: AsyncClient) -> None:
    response = await api_client.get("/users/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_users_me_returns_current_user_with_valid_token(
    api_client: AsyncClient,
    active_user: User,
) -> None:
    token = create_access_token(subject=str(active_user.id), role=active_user.role.value)
    response = await api_client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == active_user.email
    assert body["role"] == active_user.role.value


@pytest.mark.asyncio
async def test_skills_list_returns_catalog(api_client: AsyncClient, active_user: User) -> None:
    skill = Skill(
        id=uuid.UUID("00000000-0000-4000-8000-000000000010"),
        name="Python",
        category="Programming Language",
        description="Backend development",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = active_user
    skills_result = MagicMock()
    skills_result.scalars.return_value.all.return_value = [skill]

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(side_effect=[user_result, skills_result])

    app = create_app()

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db
    token = create_access_token(subject=str(active_user.id), role=active_user.role.value)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/skills/",
            headers={"Authorization": f"Bearer {token}"},
        )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["name"] == "Python"
    assert body[0]["category"] == "Programming Language"
