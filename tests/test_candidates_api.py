import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token, get_password_hash
from app.crud.candidate import list_candidates
from app.db.session import get_db
from app.main import create_app
from app.models.candidate import Candidate
from app.models.user import User, UserRole
from app.schemas.candidate import CandidateRead


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


@pytest.mark.asyncio
async def test_list_candidates_returns_paginated_response(recruiter_user: User) -> None:
    candidate = Candidate(
        id=uuid.uuid4(),
        full_name="Jane Doe",
        email="jane@example.com",
        resume_path=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    mock_session = AsyncMock()
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = recruiter_user
    mock_session.execute = AsyncMock(return_value=user_result)

    app = create_app()

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db
    token = create_access_token(subject=str(recruiter_user.id), role=recruiter_user.role.value)

    with patch(
        "app.api.candidates.crud_list_candidates",
        new_callable=AsyncMock,
        return_value=([candidate], 1),
    ):
        with patch(
            "app.api.candidates._candidate_to_read",
            new_callable=AsyncMock,
            return_value=CandidateRead(
                id=candidate.id,
                full_name=candidate.full_name,
                email=candidate.email,
                resume_path=None,
                skills=[],
                created_at=candidate.created_at,
                updated_at=candidate.updated_at,
            ),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://testserver") as client:
                response = await client.get(
                    "/candidates/?skip=0&limit=10&q=jane",
                    headers={"Authorization": f"Bearer {token}"},
                )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["skip"] == 0
    assert body["limit"] == 10
    assert len(body["items"]) == 1


@pytest.mark.asyncio
async def test_list_candidates_crud_applies_search_filter() -> None:
    candidate = Candidate(
        id=uuid.uuid4(),
        full_name="Jane Doe",
        email="jane@example.com",
        resume_path=None,
    )
    mock_db = AsyncMock()
    count_result = MagicMock()
    count_result.scalar_one.return_value = 1
    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = [candidate]
    mock_db.execute = AsyncMock(side_effect=[count_result, list_result])

    candidates, total = await list_candidates(mock_db, q="jane")

    assert total == 1
    assert len(candidates) == 1
