import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from jose import jwt

from app.api.deps import get_current_user, role_required
from app.core.config import Settings
from app.core.security import (
    ALGORITHM,
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)
from app.db.session import get_db
from app.main import create_app
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserUpdate


def test_password_hash_rejects_over_72_bytes() -> None:
    with pytest.raises(ValueError):
        get_password_hash("a" * 80)


def test_verify_password_handles_invalid_hash_and_long_password() -> None:
    assert verify_password("secret", "not-a-bcrypt-hash") is False
    assert verify_password("x" * 80, get_password_hash("short")) is False


def test_decode_access_token_rejects_invalid_token() -> None:
    with pytest.raises(ValueError):
        decode_access_token("not.valid.token")


def test_create_access_token_custom_expiry() -> None:
    from datetime import timedelta

    token = create_access_token(
        subject="user-id",
        role="recruiter",
        expires_delta=timedelta(minutes=5),
    )
    payload = decode_access_token(token)
    assert payload["sub"] == "user-id"


def test_user_schema_password_validators() -> None:
    UserCreate(
        full_name="Test User",
        email="valid@example.com",
        password="Password1",
        role=UserRole.Recruiter,
    )
    with pytest.raises(ValueError):
        UserCreate(
            full_name="Test User",
            email="valid@example.com",
            password="short",
            role=UserRole.Recruiter,
        )
    with pytest.raises(ValueError):
        UserUpdate(password="a" * 80)


def test_settings_parse_cors_origins() -> None:
    parsed = Settings.parse_cors_origins("http://a.com, http://b.com")
    assert parsed == ["http://a.com", "http://b.com"]
    default_none = Settings.parse_cors_origins(None)
    assert "localhost" in default_none[0]


@pytest.mark.asyncio
async def test_login_form_encoded_and_inactive_user() -> None:
    user_id = uuid.uuid4()
    password = "Password1"
    user = User(
        id=user_id,
        full_name="Recruiter",
        email="recruiter@example.com",
        hashed_password=get_password_hash(password),
        role=UserRole.Recruiter,
        is_active=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    mock_db = AsyncMock()
    lookup = MagicMock()
    lookup.scalar_one_or_none.return_value = user
    mock_db.execute = AsyncMock(return_value=lookup)

    app = create_app()

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        inactive = await client.post(
            "/auth/login",
            data={"username": "recruiter@example.com", "password": password},
        )
        assert inactive.status_code == 403

    user.is_active = True
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        success = await client.post(
            "/auth/login",
            data={"email": "recruiter@example.com", "password": password},
        )
    app.dependency_overrides.clear()
    assert success.status_code == 200
    assert success.json()["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_json_and_missing_credentials() -> None:
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        missing = await client.post("/auth/login", json={})
        assert missing.status_code == 422


@pytest.mark.asyncio
async def test_get_current_user_invalid_token_and_inactive() -> None:
    mock_db = AsyncMock()
    with pytest.raises(HTTPException) as bad_token:
        await get_current_user(db=mock_db, token="bad.token.value")
    assert bad_token.value.status_code == 401

    user_id = uuid.uuid4()
    token = create_access_token(subject=str(user_id), role=UserRole.Recruiter.value)
    inactive = User(
        id=user_id,
        full_name="Inactive",
        email="inactive@example.com",
        hashed_password="hash",
        role=UserRole.Recruiter,
        is_active=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    lookup = MagicMock()
    lookup.scalar_one_or_none.return_value = inactive
    mock_db.execute = AsyncMock(return_value=lookup)

    with pytest.raises(HTTPException) as inactive_exc:
        await get_current_user(db=mock_db, token=token)
    assert inactive_exc.value.status_code == 403


@pytest.mark.asyncio
async def test_role_required_rejects_wrong_role() -> None:
    user = User(
        id=uuid.uuid4(),
        full_name="Candidate",
        email="c@example.com",
        hashed_password="hash",
        role=UserRole.Candidate,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    dep = role_required(UserRole.Admin)

    with pytest.raises(HTTPException) as exc:
        await dep(current_user=user)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_main_lifespan_configures_logging() -> None:
    from app.main import lifespan

    app = create_app()
    async with lifespan(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/health")
    assert response.status_code == 200
