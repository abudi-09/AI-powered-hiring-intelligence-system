import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.crud.user import create_user, deactivate_user, get_user_by_id, update_user
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserUpdate


@pytest.mark.asyncio
async def test_create_user_rejects_duplicate_email() -> None:
    payload = UserCreate(
        full_name="Jane Doe",
        email="jane@example.com",
        password="Password123",
        role=UserRole.Recruiter,
    )
    mock_db = AsyncMock()
    existing = MagicMock()
    existing.scalar_one_or_none.return_value = object()
    mock_db.execute = AsyncMock(return_value=existing)

    with pytest.raises(HTTPException) as exc:
        await create_user(mock_db, payload)

    assert exc.value.status_code == 400
    assert exc.value.detail == "Email already exists"
    mock_db.add.assert_not_called()


@pytest.mark.asyncio
async def test_get_user_by_id_returns_404_for_missing_user() -> None:
    user_id = uuid.uuid4()
    mock_db = AsyncMock()
    lookup = MagicMock()
    lookup.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=lookup)

    with pytest.raises(HTTPException) as exc:
        await get_user_by_id(mock_db, user_id)

    assert exc.value.status_code == 404
    assert exc.value.detail == "User not found"


@pytest.mark.asyncio
async def test_deactivate_user_sets_inactive_flag() -> None:
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        full_name="Jane Doe",
        email="jane@example.com",
        hashed_password="hashed",
        role=UserRole.Recruiter,
        is_active=True,
    )
    mock_db = AsyncMock()
    lookup = MagicMock()
    lookup.scalar_one_or_none.return_value = user
    mock_db.execute = AsyncMock(return_value=lookup)

    result = await deactivate_user(mock_db, user_id)

    assert result.is_active is False
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_user_applies_partial_fields() -> None:
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        full_name="Jane Doe",
        email="jane@example.com",
        hashed_password="hashed",
        role=UserRole.Recruiter,
        is_active=True,
    )
    mock_db = AsyncMock()
    lookup = MagicMock()
    lookup.scalar_one_or_none.return_value = user
    mock_db.execute = AsyncMock(return_value=lookup)

    result = await update_user(
        mock_db,
        user_id,
        UserUpdate(full_name="Jane Smith", role=UserRole.Admin),
    )

    assert result.full_name == "Jane Smith"
    assert result.role == UserRole.Admin
    mock_db.commit.assert_awaited_once()
