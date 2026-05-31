import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token, get_password_hash
from app.db.session import get_db
from app.main import create_app
from app.models.recommendation import Recommendation
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
async def narratives_client(recruiter_user: User):
    mock_session = AsyncMock()
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = recruiter_user

    app = create_app()

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db
    token = create_access_token(subject=str(recruiter_user.id), role=recruiter_user.role.value)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client, token, mock_session, user_result

    app.dependency_overrides.clear()


def _recommendation(recommendation_id: uuid.UUID) -> Recommendation:
    return Recommendation(
        id=recommendation_id,
        entity_type="job",
        entity_id=uuid.uuid4(),
        recommended_entity_id=uuid.uuid4(),
        recommendation_type="candidate_match",
        rank=1,
        score=90.0,
        confidence=85.0,
        explanation={"summary": "Strong fit"},
        created_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_generate_recommendation_narrative_returns_text(narratives_client) -> None:
    client, token, mock_session, user_result = narratives_client
    recommendation_id = uuid.uuid4()
    recommendation = _recommendation(recommendation_id)
    db_result = MagicMock()
    db_result.scalar_one_or_none.return_value = recommendation
    mock_session.execute = AsyncMock(side_effect=[user_result, db_result])

    narrative_payload = {
        "recommendation_id": recommendation_id,
        "narrative_text": "Strong Python overlap for this backend role.",
        "summary_bullets": ["Python", "FastAPI"],
        "tone_used": "professional",
        "confidence": 88.0,
        "version": "v1",
    }

    with patch(
        "app.api.narratives.NarrativeEngine.generate_narrative",
        new_callable=AsyncMock,
        return_value=narrative_payload,
    ):
        response = await client.post(
            f"/narratives/recommendation/{recommendation_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "recommendation_id": str(recommendation_id),
                "tone": "professional",
                "include_bullets": True,
            },
        )

    assert response.status_code == 200
    assert "Strong Python overlap" in response.json()["narrative_text"]


@pytest.mark.asyncio
async def test_generate_recommendation_narrative_returns_404(narratives_client) -> None:
    client, token, mock_session, user_result = narratives_client
    recommendation_id = uuid.uuid4()
    db_result = MagicMock()
    db_result.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(side_effect=[user_result, db_result])

    response = await client.post(
        f"/narratives/recommendation/{recommendation_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "recommendation_id": str(recommendation_id),
            "tone": "professional",
            "include_bullets": True,
        },
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_generate_batch_narratives_returns_list(narratives_client) -> None:
    client, token, mock_session, user_result = narratives_client
    recommendation_id = uuid.uuid4()
    recommendation = _recommendation(recommendation_id)
    db_result = MagicMock()
    db_result.scalars.return_value.all.return_value = [recommendation]
    mock_session.execute = AsyncMock(side_effect=[user_result, db_result])

    narrative_payload = {
        "recommendation_id": recommendation_id,
        "narrative_text": "Batch narrative",
        "summary_bullets": ["Skill match"],
        "tone_used": "neutral",
        "confidence": 80.0,
        "version": "v1",
    }

    with patch(
        "app.api.narratives.NarrativeEngine.generate_narrative",
        new_callable=AsyncMock,
        return_value=narrative_payload,
    ):
        response = await client.post(
            "/narratives/batch",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "recommendation_ids": [str(recommendation_id)],
                "tone": "neutral",
                "include_bullets": False,
            },
        )

    assert response.status_code == 200
    assert response.json()["total"] == 1


@pytest.mark.asyncio
async def test_narratives_routes_require_authentication() -> None:
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            f"/narratives/recommendation/{uuid.uuid4()}",
            json={
                "recommendation_id": str(uuid.uuid4()),
                "tone": "professional",
                "include_bullets": True,
            },
        )

    assert response.status_code == 401
