import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token, get_password_hash
from app.db.session import get_db
from app.main import create_app
from app.models.match import MatchScore
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
def job_id() -> uuid.UUID:
    return uuid.UUID("00000000-0000-4000-8000-000000000050")


@pytest.mark.asyncio
async def test_auto_score_job_matches_endpoint_returns_batch_result(
    recruiter_user: User,
    job_id: uuid.UUID,
) -> None:
    candidate_id = uuid.UUID("00000000-0000-4000-8000-000000000051")
    match = MatchScore(
        id=uuid.uuid4(),
        candidate_id=candidate_id,
        job_id=job_id,
        score=91.5,
        explanation={"final_score": 91.5},
        created_at=datetime.now(timezone.utc),
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
        "app.api.jobs.batch_auto_score_job_matches",
        new_callable=AsyncMock,
        return_value=[match],
    ) as batch_score:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(
                f"/jobs/{job_id}/matches/auto-score",
                headers={"Authorization": f"Bearer {token}"},
                json={"candidate_ids": [str(candidate_id)]},
            )

    app.dependency_overrides.clear()

    assert response.status_code == 201
    body = response.json()
    assert body["job_id"] == str(job_id)
    assert body["scored_count"] == 1
    assert body["matches"][0]["score"] == pytest.approx(91.5)
    batch_score.assert_awaited_once_with(mock_session, job_id, [candidate_id])


@pytest.mark.asyncio
async def test_auto_score_job_matches_requires_authentication(job_id: uuid.UUID) -> None:
    app = create_app()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(f"/jobs/{job_id}/matches/auto-score")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_auto_score_job_matches_propagates_job_not_found(
    recruiter_user: User,
    job_id: uuid.UUID,
) -> None:
    from fastapi import HTTPException

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
        "app.api.jobs.batch_auto_score_job_matches",
        new_callable=AsyncMock,
        side_effect=HTTPException(status_code=400, detail="Job not found"),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(
                f"/jobs/{job_id}/matches/auto-score",
                headers={"Authorization": f"Bearer {token}"},
            )

    app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json()["detail"] == "Job not found"
