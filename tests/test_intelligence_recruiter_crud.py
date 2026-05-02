import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.crud.intelligence import generate_recruiter_performance
from app.models.user import User, UserRole


@pytest.mark.asyncio
async def test_generate_recruiter_performance_rejects_unknown_user() -> None:
    recruiter_id = uuid.uuid4()
    mock_db = AsyncMock()
    lookup = MagicMock()
    lookup.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=lookup)

    with pytest.raises(HTTPException) as exc:
        await generate_recruiter_performance(mock_db, recruiter_id)

    assert exc.value.status_code == 404
    assert exc.value.detail == "Recruiter not found"


@pytest.mark.asyncio
async def test_generate_recruiter_performance_rejects_non_recruiter_role() -> None:
    recruiter_id = uuid.uuid4()
    user = User(
        id=recruiter_id,
        full_name="Candidate User",
        email="candidate@example.com",
        hashed_password="hashed",
        role=UserRole.Candidate,
        is_active=True,
    )
    mock_db = AsyncMock()
    lookup = MagicMock()
    lookup.scalar_one_or_none.return_value = user
    mock_db.execute = AsyncMock(return_value=lookup)

    with pytest.raises(HTTPException) as exc:
        await generate_recruiter_performance(mock_db, recruiter_id)

    assert exc.value.status_code == 400
    assert exc.value.detail == "User is not a recruiter"
