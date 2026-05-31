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
async def matches_client(recruiter_user: User):
    mock_session = AsyncMock()
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = recruiter_user
    mock_session.execute = AsyncMock(return_value=user_result)

    app = create_app()

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db
    token = create_access_token(subject=str(recruiter_user.id), role=recruiter_user.role.value)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client, token

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_auto_score_match_endpoint_returns_match(matches_client) -> None:
    client, token = matches_client
    candidate_id = uuid.uuid4()
    job_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    match = MatchScore(
        id=uuid.uuid4(),
        candidate_id=candidate_id,
        job_id=job_id,
        score=88.0,
        explanation={"final_score": 88.0},
        created_at=now,
        updated_at=now,
    )

    with patch(
        "app.api.matches.calculate_match_score",
        new_callable=AsyncMock,
        return_value=(88.0, {"final_score": 88.0}),
    ), patch(
        "app.api.matches.upsert_match_score",
        new_callable=AsyncMock,
        return_value=match,
    ):
        response = await client.post(
            "/matches/auto-score",
            headers={"Authorization": f"Bearer {token}"},
            json={"candidate_id": str(candidate_id), "job_id": str(job_id)},
        )

    assert response.status_code == 201
    body = response.json()
    assert body["score"] == pytest.approx(88.0)
    assert body["candidate_id"] == str(candidate_id)


@pytest.mark.asyncio
async def test_top_candidates_for_job_returns_ranked_matches(matches_client) -> None:
    client, token = matches_client
    job_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    matches = [
        MatchScore(
            id=uuid.uuid4(),
            candidate_id=uuid.uuid4(),
            job_id=job_id,
            score=91.0,
            explanation={},
            created_at=now,
            updated_at=now,
        )
    ]

    with patch(
        "app.api.matches.get_top_candidates",
        new_callable=AsyncMock,
        return_value=matches,
    ):
        response = await client.get(
            f"/matches/top-candidates/{job_id}?limit=5",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["score"] == pytest.approx(91.0)


@pytest.mark.asyncio
async def test_matches_routes_require_authentication() -> None:
    job_id = uuid.uuid4()
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(f"/matches/by-job/{job_id}")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_manual_score_and_list_match_routes(matches_client) -> None:
    client, token = matches_client
    candidate_id = uuid.uuid4()
    job_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    match = MatchScore(
        id=uuid.uuid4(),
        candidate_id=candidate_id,
        job_id=job_id,
        score=77.0,
        explanation={"final_score": 77.0},
        created_at=now,
        updated_at=now,
    )

    with patch(
        "app.api.matches.upsert_match_score",
        new_callable=AsyncMock,
        return_value=match,
    ), patch(
        "app.api.matches.get_matches_by_job",
        new_callable=AsyncMock,
        return_value=[match],
    ), patch(
        "app.api.matches.get_matches_by_candidate",
        new_callable=AsyncMock,
        return_value=[match],
    ), patch(
        "app.api.matches.get_top_jobs",
        new_callable=AsyncMock,
        return_value=[match],
    ):
        manual_response = await client.post(
            "/matches/manual",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "candidate_id": str(candidate_id),
                "job_id": str(job_id),
                "score": 77.0,
                "explanation": {"final_score": 77.0},
            },
        )
        by_job_response = await client.get(
            f"/matches/by-job/{job_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        by_candidate_response = await client.get(
            f"/matches/by-candidate/{candidate_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        top_jobs_response = await client.get(
            f"/matches/top-jobs/{candidate_id}?limit=3",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert manual_response.status_code == 201
    assert by_job_response.status_code == 200
    assert by_candidate_response.status_code == 200
    assert top_jobs_response.status_code == 200
