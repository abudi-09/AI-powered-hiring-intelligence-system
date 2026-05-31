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
def admin_user() -> User:
    now = datetime.now(timezone.utc)
    return User(
        id=uuid.UUID("00000000-0000-4000-8000-000000000010"),
        email="admin@example.com",
        hashed_password=get_password_hash("Password123"),
        full_name="Admin User",
        role=UserRole.Admin,
        is_active=True,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
async def users_client(admin_user: User):
    mock_session = AsyncMock()
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = admin_user
    mock_session.execute = AsyncMock(return_value=user_result)

    app = create_app()

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db
    token = create_access_token(subject=str(admin_user.id), role=admin_user.role.value)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client, token

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_users_me_returns_current_user(admin_user: User) -> None:
    mock_session = AsyncMock()
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = admin_user
    mock_session.execute = AsyncMock(return_value=user_result)

    app = create_app()

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db
    token = create_access_token(subject=str(admin_user.id), role=admin_user.role.value)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["email"] == "admin@example.com"


@pytest.mark.asyncio
async def test_list_users_returns_admin_only_route(users_client, admin_user: User) -> None:
    client, token = users_client

    with patch(
        "app.api.users.crud_list_users",
        new_callable=AsyncMock,
        return_value=[admin_user],
    ):
        response = await client.get(
            "/users/",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    assert len(response.json()) == 1


@pytest.mark.asyncio
async def test_create_and_get_user_routes(users_client, admin_user: User) -> None:
    client, token = users_client
    user_id = uuid.uuid4()
    created = User(
        id=user_id,
        email="new@example.com",
        hashed_password=admin_user.hashed_password,
        full_name="New User",
        role=UserRole.Recruiter,
        is_active=True,
        created_at=admin_user.created_at,
        updated_at=admin_user.updated_at,
    )

    with patch(
        "app.api.users.crud_create_user",
        new_callable=AsyncMock,
        return_value=created,
    ), patch(
        "app.api.users.crud_get_user_by_id",
        new_callable=AsyncMock,
        return_value=created,
    ):
        create_response = await client.post(
            "/users/",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "full_name": "New User",
                "email": "new@example.com",
                "password": "Password123",
                "role": "Recruiter",
            },
        )
        get_response = await client.get(
            f"/users/{user_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert create_response.status_code == 201
    assert get_response.status_code == 200
    assert get_response.json()["email"] == "new@example.com"


@pytest.mark.asyncio
async def test_update_and_deactivate_user_routes(users_client, admin_user: User) -> None:
    client, token = users_client
    user_id = uuid.uuid4()
    updated = User(
        id=user_id,
        email="updated@example.com",
        hashed_password=admin_user.hashed_password,
        full_name="Updated User",
        role=UserRole.Recruiter,
        is_active=False,
        created_at=admin_user.created_at,
        updated_at=admin_user.updated_at,
    )

    with patch(
        "app.api.users.crud_update_user",
        new_callable=AsyncMock,
        return_value=updated,
    ), patch(
        "app.api.users.crud_deactivate_user",
        new_callable=AsyncMock,
        return_value=updated,
    ):
        patch_response = await client.patch(
            f"/users/{user_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"full_name": "Updated User"},
        )
        deactivate_response = await client.post(
            f"/users/{user_id}/deactivate",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert patch_response.status_code == 200
    assert deactivate_response.status_code == 200
    assert deactivate_response.json()["is_active"] is False
