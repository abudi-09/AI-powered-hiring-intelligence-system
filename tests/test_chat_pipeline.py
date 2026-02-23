import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token, get_password_hash
from app.db.session import get_db
from app.main import create_app
from app.models.conversation import ConversationMessage, ConversationSession
from app.models.user import User, UserRole
from app.services.analytics_engine import AnalyticsEngine
from app.services.insight_engine import InsightEngine


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
def session_id() -> uuid.UUID:
    return uuid.UUID("00000000-0000-4000-8000-000000000060")


@pytest.fixture
def job_id() -> uuid.UUID:
    return uuid.UUID("00000000-0000-4000-8000-000000000061")


def _session(
    session_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    title: str = "Test session",
    context: dict | None = None,
    messages: list[ConversationMessage] | None = None,
) -> ConversationSession:
    now = datetime.now(timezone.utc)
    session = ConversationSession(
        id=session_id,
        user_id=user_id,
        title=title,
        context=context or {},
        created_at=now,
        updated_at=now,
    )
    session.messages = messages or []
    return session


@pytest.fixture
async def chat_client(recruiter_user: User):
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
        yield client, token, mock_session

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_chat_help_query_creates_session_and_persists_messages(
    chat_client,
    recruiter_user: User,
    session_id: uuid.UUID,
) -> None:
    client, token, _ = chat_client
    created = _session(session_id, recruiter_user.id, title="hello there")

    with patch("app.api.chat.conversation_crud.create_session", new_callable=AsyncMock, return_value=created):
        with patch("app.api.chat.conversation_crud.create_message", new_callable=AsyncMock) as create_message:
            with patch(
                "app.api.chat.conversation_crud.update_session_context",
                new_callable=AsyncMock,
            ) as update_context:
                response = await client.post(
                    "/chat/query",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"query": "hello there"},
                )

    assert response.status_code == 200
    body = response.json()
    assert body["session_id"] == str(session_id)
    assert body["intent"] == "general_help"
    assert "recruiter assistant" in body["message"]
    assert create_message.await_count == 2
    update_context.assert_awaited_once()


@pytest.mark.asyncio
async def test_chat_job_analysis_runs_intent_plan_orchestrator_pipeline(
    chat_client,
    recruiter_user: User,
    session_id: uuid.UUID,
    job_id: uuid.UUID,
) -> None:
    client, token, _ = chat_client
    created = _session(session_id, recruiter_user.id)
    job_analytics = {
        "average_match_score": 74.5,
        "candidate_count": 8,
        "hiring_difficulty_score": 58.0,
    }
    job_insights = [{"severity": "high", "insight_type": "hiring_risk", "title": "Risk"}]
    matches = [SimpleNamespace(score=89.0)]

    with patch("app.api.chat.conversation_crud.create_session", new_callable=AsyncMock, return_value=created):
        with patch("app.api.chat.conversation_crud.create_message", new_callable=AsyncMock):
            with patch("app.api.chat.conversation_crud.update_session_context", new_callable=AsyncMock):
                with patch.object(
                    AnalyticsEngine,
                    "compute_job_analytics",
                    new_callable=AsyncMock,
                    return_value=job_analytics,
                ):
                    with patch.object(
                        InsightEngine,
                        "generate_job_insights",
                        new_callable=AsyncMock,
                        return_value=job_insights,
                    ):
                        with patch(
                            "app.services.conversation_orchestrator.get_matches_by_job",
                            new_callable=AsyncMock,
                            return_value=matches,
                        ):
                            response = await client.post(
                                "/chat/query",
                                headers={"Authorization": f"Bearer {token}"},
                                json={
                                    "query": f"Why is job {job_id} hard to hire for?",
                                },
                            )

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "job_analysis"
    assert body["entities"]["entity_type"] == "job"
    assert body["entities"]["entity_id"] == str(job_id)
    assert "74.5%" in body["message"]
    assert "analytics" in body["sources"]
    assert body["confidence"] >= 85.0


@pytest.mark.asyncio
async def test_chat_job_analysis_without_entity_requests_clarification(
    chat_client,
    recruiter_user: User,
    session_id: uuid.UUID,
) -> None:
    client, token, _ = chat_client
    created = _session(session_id, recruiter_user.id)

    with patch("app.api.chat.conversation_crud.create_session", new_callable=AsyncMock, return_value=created):
        with patch("app.api.chat.conversation_crud.create_message", new_callable=AsyncMock):
            with patch("app.api.chat.conversation_crud.update_session_context", new_callable=AsyncMock):
                response = await client.post(
                    "/chat/query",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"query": "Why is this job hard to hire for?"},
                )

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "job_analysis"
    assert "job ID or candidate ID" in body["message"]
    assert body["confidence"] == pytest.approx(100.0)


@pytest.mark.asyncio
async def test_chat_query_reuses_existing_session(
    chat_client,
    recruiter_user: User,
    session_id: uuid.UUID,
) -> None:
    client, token, _ = chat_client
    existing = _session(
        session_id,
        recruiter_user.id,
        context={
            "last_intent": "job_analysis",
            "last_entity_type": "job",
            "last_entity_id": str(uuid.uuid4()),
        },
    )

    with patch(
        "app.api.chat.conversation_crud.get_session",
        new_callable=AsyncMock,
        return_value=existing,
    ) as get_session:
        with patch("app.api.chat.conversation_crud.create_session", new_callable=AsyncMock) as create_session:
            with patch("app.api.chat.conversation_crud.create_message", new_callable=AsyncMock):
                with patch("app.api.chat.conversation_crud.update_session_context", new_callable=AsyncMock):
                    response = await client.post(
                        "/chat/query",
                        headers={"Authorization": f"Bearer {token}"},
                        json={
                            "query": "hello again",
                            "session_id": str(session_id),
                        },
                    )

    assert response.status_code == 200
    get_session.assert_awaited_once()
    create_session.assert_not_awaited()


@pytest.mark.asyncio
async def test_chat_query_returns_404_for_unknown_session(
    chat_client,
    session_id: uuid.UUID,
) -> None:
    client, token, _ = chat_client

    with patch("app.api.chat.conversation_crud.get_session", new_callable=AsyncMock, return_value=None):
        response = await client.post(
            "/chat/query",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "query": "continue our conversation",
                "session_id": str(session_id),
            },
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Session not found"


@pytest.mark.asyncio
async def test_chat_follow_up_uses_session_context_for_entity(
    chat_client,
    recruiter_user: User,
    session_id: uuid.UUID,
    job_id: uuid.UUID,
) -> None:
    client, token, _ = chat_client
    existing = _session(
        session_id,
        recruiter_user.id,
        context={
            "last_intent": "job_analysis",
            "last_entity_type": "job",
            "last_entity_id": str(job_id),
        },
    )
    job_analytics = {
        "average_match_score": 70.0,
        "candidate_count": 4,
        "hiring_difficulty_score": 50.0,
    }

    with patch("app.api.chat.conversation_crud.get_session", new_callable=AsyncMock, return_value=existing):
        with patch("app.api.chat.conversation_crud.create_message", new_callable=AsyncMock):
            with patch("app.api.chat.conversation_crud.update_session_context", new_callable=AsyncMock):
                with patch.object(
                    AnalyticsEngine,
                    "compute_job_analytics",
                    new_callable=AsyncMock,
                    return_value=job_analytics,
                ) as compute_analytics:
                    with patch.object(
                        InsightEngine,
                        "generate_job_insights",
                        new_callable=AsyncMock,
                        return_value=[],
                    ):
                        with patch(
                            "app.services.conversation_orchestrator.get_matches_by_job",
                            new_callable=AsyncMock,
                            return_value=[],
                        ):
                            response = await client.post(
                                "/chat/query",
                                headers={"Authorization": f"Bearer {token}"},
                                json={
                                    "query": "Show me the candidate pool for this job",
                                    "session_id": str(session_id),
                                },
                            )

    assert response.status_code == 200
    body = response.json()
    assert body["entities"]["entity_id"] == str(job_id)
    compute_analytics.assert_awaited_once_with(job_id)


@pytest.mark.asyncio
async def test_list_chat_sessions_for_current_user(
    chat_client,
    recruiter_user: User,
    session_id: uuid.UUID,
) -> None:
    client, token, _ = chat_client
    session = _session(session_id, recruiter_user.id, messages=[MagicMock(), MagicMock()])

    with patch(
        "app.api.chat.conversation_crud.list_user_sessions",
        new_callable=AsyncMock,
        return_value=[session],
    ):
        response = await client.get(
            "/chat/sessions",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == str(session_id)
    assert body[0]["message_count"] == 2


@pytest.mark.asyncio
async def test_get_chat_session_detail_returns_messages(
    chat_client,
    recruiter_user: User,
    session_id: uuid.UUID,
) -> None:
    client, token, _ = chat_client
    now = datetime.now(timezone.utc)
    messages = [
        ConversationMessage(
            id=uuid.uuid4(),
            session_id=session_id,
            role="user",
            content="hello",
            intent=None,
            entities=None,
            confidence=None,
            sources=None,
            created_at=now,
        ),
        ConversationMessage(
            id=uuid.uuid4(),
            session_id=session_id,
            role="assistant",
            content="Hi there",
            intent="general_help",
            entities={},
            confidence=100.0,
            sources=["system"],
            created_at=now,
        ),
    ]
    session = _session(session_id, recruiter_user.id, messages=messages)

    with patch(
        "app.api.chat.conversation_crud.get_session",
        new_callable=AsyncMock,
        return_value=session,
    ):
        response = await client.get(
            f"/chat/session/{session_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(session_id)
    assert len(body["messages"]) == 2
    assert body["messages"][0]["role"] == "user"
    assert body["messages"][1]["intent"] == "general_help"


@pytest.mark.asyncio
async def test_delete_chat_session(
    chat_client,
    session_id: uuid.UUID,
) -> None:
    client, token, _ = chat_client

    with patch(
        "app.api.chat.conversation_crud.delete_session",
        new_callable=AsyncMock,
        return_value=True,
    ):
        response = await client.delete(
            f"/chat/session/{session_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    assert response.json()["message"] == "Session deleted successfully"
