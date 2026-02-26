import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token, get_password_hash
from app.db.session import get_db
from app.main import create_app
from app.models.skill import Skill
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


@pytest.mark.asyncio
async def test_create_skill_endpoint_delegates_to_crud(admin_user: User) -> None:
    skill = Skill(
        id=uuid.uuid4(),
        name="Kubernetes",
        category="Infrastructure",
        created_at=datetime.now(timezone.utc),
    )

    mock_session = AsyncMock()
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = admin_user
    mock_session.execute = AsyncMock(return_value=user_result)

    app = create_app()

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db
    token = create_access_token(subject=str(admin_user.id), role=admin_user.role.value)

    with patch(
        "app.api.skills.crud_create_skill",
        new_callable=AsyncMock,
        return_value=skill,
    ) as create_skill:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(
                "/skills/",
                headers={"Authorization": f"Bearer {token}"},
                json={"name": "Kubernetes", "category": "Infrastructure"},
            )

    app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["name"] == "Kubernetes"
    create_skill.assert_awaited_once()
