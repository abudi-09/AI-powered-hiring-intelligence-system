import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token, get_password_hash
from app.db.session import get_db
from app.main import create_app
from app.models.intelligence import (
    CandidateIntelligence,
    JobIntelligence,
    MatchIntelligence,
    SkillIntelligence,
)
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
async def intelligence_client(recruiter_user: User):
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


def _job_intelligence(job_id: uuid.UUID) -> JobIntelligence:
    return JobIntelligence(
        id=uuid.uuid4(),
        job_id=job_id,
        hiring_difficulty_score=62.0,
        candidate_availability_ratio=1.4,
        skill_scarcity_index=71.0,
        avg_match_score=78.5,
        breakdown={"matched_candidates": 6},
        created_at=datetime.now(timezone.utc),
    )


def _candidate_intelligence(candidate_id: uuid.UUID) -> CandidateIntelligence:
    return CandidateIntelligence(
        id=uuid.uuid4(),
        candidate_id=candidate_id,
        market_competitiveness_score=80.0,
        versatility_index=65.0,
        skill_depth_score=72.0,
        growth_potential_score=68.0,
        breakdown={"matched_jobs": 3},
        created_at=datetime.now(timezone.utc),
    )


def _skill_intelligence(skill_id: uuid.UUID) -> SkillIntelligence:
    return SkillIntelligence(
        id=uuid.uuid4(),
        skill_id=skill_id,
        demand_count=8,
        supply_count=3,
        scarcity_ratio=2.67,
        avg_required_level=70.0,
        breakdown={"open_jobs": 8},
        created_at=datetime.now(timezone.utc),
    )


def _match_intelligence() -> MatchIntelligence:
    return MatchIntelligence(
        id=uuid.uuid4(),
        score_distribution={"80-100": 4, "60-79": 9},
        top_percentile_score=91.0,
        low_match_ratio=18.0,
        recommendation_quality_index=74.0,
        created_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_get_job_intelligence_returns_snapshot(intelligence_client) -> None:
    client, token = intelligence_client
    job_id = uuid.uuid4()
    intelligence = _job_intelligence(job_id)

    with patch(
        "app.api.intelligence.intelligence_crud.get_job_intelligence",
        new_callable=AsyncMock,
        return_value=intelligence,
    ):
        response = await client.get(
            f"/intelligence/job/{job_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == str(job_id)
    assert body["hiring_difficulty_score"] == pytest.approx(62.0)


@pytest.mark.asyncio
async def test_generate_job_intelligence_returns_created_row(intelligence_client) -> None:
    client, token = intelligence_client
    job_id = uuid.uuid4()
    intelligence = _job_intelligence(job_id)

    with patch(
        "app.api.intelligence.intelligence_crud.generate_job_intelligence",
        new_callable=AsyncMock,
        return_value=intelligence,
    ):
        response = await client.post(
            f"/intelligence/generate/job/{job_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 201
    assert response.json()["avg_match_score"] == pytest.approx(78.5)


@pytest.mark.asyncio
async def test_generate_job_intelligence_maps_missing_job_to_404(intelligence_client) -> None:
    client, token = intelligence_client
    job_id = uuid.uuid4()

    with patch(
        "app.api.intelligence.intelligence_crud.generate_job_intelligence",
        new_callable=AsyncMock,
        side_effect=ValueError("Job not found"),
    ):
        response = await client.post(
            f"/intelligence/generate/job/{job_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Job not found"


@pytest.mark.asyncio
async def test_get_candidate_intelligence_returns_snapshot(intelligence_client) -> None:
    client, token = intelligence_client
    candidate_id = uuid.uuid4()
    intelligence = _candidate_intelligence(candidate_id)

    with patch(
        "app.api.intelligence.intelligence_crud.get_candidate_intelligence",
        new_callable=AsyncMock,
        return_value=intelligence,
    ):
        response = await client.get(
            f"/intelligence/candidate/{candidate_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    assert response.json()["market_competitiveness_score"] == pytest.approx(80.0)


@pytest.mark.asyncio
async def test_generate_candidate_intelligence_returns_created_row(intelligence_client) -> None:
    client, token = intelligence_client
    candidate_id = uuid.uuid4()
    intelligence = _candidate_intelligence(candidate_id)

    with patch(
        "app.api.intelligence.intelligence_crud.generate_candidate_intelligence",
        new_callable=AsyncMock,
        return_value=intelligence,
    ):
        response = await client.post(
            f"/intelligence/generate/candidate/{candidate_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 201
    assert response.json()["candidate_id"] == str(candidate_id)


@pytest.mark.asyncio
async def test_get_skill_intelligence_returns_snapshot(intelligence_client) -> None:
    client, token = intelligence_client
    skill_id = uuid.uuid4()
    intelligence = _skill_intelligence(skill_id)

    with patch(
        "app.api.intelligence.intelligence_crud.get_skill_intelligence",
        new_callable=AsyncMock,
        return_value=intelligence,
    ):
        response = await client.get(
            f"/intelligence/skill/{skill_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    assert response.json()["demand_count"] == 8


@pytest.mark.asyncio
async def test_generate_skill_intelligence_returns_created_row(intelligence_client) -> None:
    client, token = intelligence_client
    skill_id = uuid.uuid4()
    intelligence = _skill_intelligence(skill_id)

    with patch(
        "app.api.intelligence.intelligence_crud.generate_skill_intelligence",
        new_callable=AsyncMock,
        return_value=intelligence,
    ):
        response = await client.post(
            f"/intelligence/generate/skill/{skill_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 201
    assert response.json()["scarcity_ratio"] == pytest.approx(2.67)


@pytest.mark.asyncio
async def test_get_job_intelligence_returns_404_when_missing(intelligence_client) -> None:
    client, token = intelligence_client
    job_id = uuid.uuid4()

    with patch(
        "app.api.intelligence.intelligence_crud.get_job_intelligence",
        new_callable=AsyncMock,
        return_value=None,
    ):
        response = await client.get(
            f"/intelligence/job/{job_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_generate_candidate_intelligence_maps_missing_candidate_to_404(
    intelligence_client,
) -> None:
    client, token = intelligence_client
    candidate_id = uuid.uuid4()

    with patch(
        "app.api.intelligence.intelligence_crud.generate_candidate_intelligence",
        new_callable=AsyncMock,
        side_effect=ValueError("Candidate not found"),
    ):
        response = await client.post(
            f"/intelligence/generate/candidate/{candidate_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Candidate not found"


@pytest.mark.asyncio
async def test_get_skill_intelligence_returns_404_when_missing(intelligence_client) -> None:
    client, token = intelligence_client
    skill_id = uuid.uuid4()

    with patch(
        "app.api.intelligence.intelligence_crud.get_skill_intelligence",
        new_callable=AsyncMock,
        return_value=None,
    ):
        response = await client.get(
            f"/intelligence/skill/{skill_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_generate_skill_intelligence_maps_missing_skill_to_404(intelligence_client) -> None:
    client, token = intelligence_client
    skill_id = uuid.uuid4()

    with patch(
        "app.api.intelligence.intelligence_crud.generate_skill_intelligence",
        new_callable=AsyncMock,
        side_effect=ValueError("Skill not found"),
    ):
        response = await client.post(
            f"/intelligence/generate/skill/{skill_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Skill not found"


@pytest.mark.asyncio
async def test_get_match_intelligence_returns_snapshot(intelligence_client) -> None:
    client, token = intelligence_client
    intelligence = _match_intelligence()

    with patch(
        "app.api.intelligence.intelligence_crud.get_match_intelligence",
        new_callable=AsyncMock,
        return_value=intelligence,
    ):
        response = await client.get(
            "/intelligence/match/summary",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    assert response.json()["top_percentile_score"] == pytest.approx(91.0)


@pytest.mark.asyncio
async def test_get_match_intelligence_returns_404_when_missing(intelligence_client) -> None:
    client, token = intelligence_client

    with patch(
        "app.api.intelligence.intelligence_crud.get_match_intelligence",
        new_callable=AsyncMock,
        return_value=None,
    ):
        response = await client.get(
            "/intelligence/match/summary",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_generate_match_intelligence_returns_created_row(intelligence_client) -> None:
    client, token = intelligence_client
    intelligence = _match_intelligence()

    with patch(
        "app.api.intelligence.intelligence_crud.generate_match_intelligence",
        new_callable=AsyncMock,
        return_value=intelligence,
    ):
        response = await client.post(
            "/intelligence/generate/match",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 201
    assert response.json()["recommendation_quality_index"] == pytest.approx(74.0)


@pytest.mark.asyncio
async def test_intelligence_routes_require_authentication() -> None:
    job_id = uuid.uuid4()
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(f"/intelligence/job/{job_id}")

    assert response.status_code == 401
