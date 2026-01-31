import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import get_password_hash
from app.db.session import get_db
from app.main import create_app
from app.models.user import User, UserRole


@pytest.fixture
def active_user() -> User:
    return User(
        id=uuid.UUID("00000000-0000-4000-8000-000000000001"),
        email="recruiter@example.com",
        hashed_password=get_password_hash("Password123"),
        full_name="Recruiter User",
        role=UserRole.Recruiter,
        is_active=True,
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
