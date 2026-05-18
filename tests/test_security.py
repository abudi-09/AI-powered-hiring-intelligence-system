import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token, get_password_hash, verify_password
from app.db.session import get_db
from app.main import create_app
from app.models.user import User, UserRole


def test_password_hash_and_verify_roundtrip() -> None:
    hashed = get_password_hash("candidate-portal-password")
    assert verify_password("candidate-portal-password", hashed)
    assert not verify_password("wrong-password", hashed)


def _build_user(role: UserRole, *, is_active: bool = True) -> User:
    now = datetime.now(timezone.utc)
    return User(
        id=uuid.UUID("00000000-0000-4000-8000-000000000030"),
        email="user@example.com",
        hashed_password=get_password_hash("Password123"),
        full_name="Test User",
        role=role,
        is_active=is_active,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_inactive_user_cannot_access_protected_routes() -> None:
    user = _build_user(UserRole.Recruiter, is_active=False)
    mock_session = AsyncMock()
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = user
    mock_session.execute = AsyncMock(return_value=user_result)

    app = create_app()

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db
    token = create_access_token(subject=str(user.id), role=user.role.value)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/analytics/skills/demand",
            headers={"Authorization": f"Bearer {token}"},
        )

    app.dependency_overrides.clear()
    assert response.status_code == 403
    assert response.json()["detail"] == "Inactive user"


@pytest.mark.asyncio
async def test_candidate_role_is_blocked_from_recruiter_routes() -> None:
    user = _build_user(UserRole.Candidate)
    mock_session = AsyncMock()
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = user
    mock_session.execute = AsyncMock(return_value=user_result)

    app = create_app()

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db
    token = create_access_token(subject=str(user.id), role=user.role.value)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/matches/by-job/00000000-0000-4000-8000-000000000099",
            headers={"Authorization": f"Bearer {token}"},
        )

    app.dependency_overrides.clear()
    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"

