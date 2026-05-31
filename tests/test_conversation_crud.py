import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.crud.conversation import (
    create_message,
    create_session,
    delete_session,
    get_session,
    get_session_messages,
    update_session_context,
)
from app.models.conversation import ConversationMessage, ConversationSession


@pytest.mark.asyncio
async def test_create_session_persists_row() -> None:
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    user_id = uuid.uuid4()

    session = await create_session(mock_db, user_id, title="Hiring chat")

    assert session.user_id == user_id
    mock_db.add.assert_called_once()
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_session_returns_loaded_session() -> None:
    mock_db = AsyncMock()
    user_id = uuid.uuid4()
    session_id = uuid.uuid4()
    session = ConversationSession(
        id=session_id,
        user_id=user_id,
        title="Chat",
        context={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    result = MagicMock()
    result.scalar_one_or_none.return_value = session
    mock_db.execute = AsyncMock(return_value=result)

    loaded = await get_session(mock_db, session_id, user_id)

    assert loaded is session


@pytest.mark.asyncio
async def test_update_session_context_commits_when_found() -> None:
    mock_db = AsyncMock()
    session = ConversationSession(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        title="Chat",
        context={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    result = MagicMock()
    result.scalar_one_or_none.return_value = session
    mock_db.execute = AsyncMock(return_value=result)
    mock_db.commit = AsyncMock()

    await update_session_context(mock_db, session.id, {"job_id": str(uuid.uuid4())})

    assert session.context["job_id"]
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_session_returns_rowcount_flag() -> None:
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(rowcount=1))
    mock_db.commit = AsyncMock()

    deleted = await delete_session(mock_db, uuid.uuid4(), uuid.uuid4())

    assert deleted is True


@pytest.mark.asyncio
async def test_create_message_and_list_messages() -> None:
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    session_id = uuid.uuid4()

    message = await create_message(
        mock_db,
        session_id,
        role="user",
        content="Show top candidates",
        intent="top_candidates",
    )
    assert message.session_id == session_id

    listed = ConversationMessage(
        id=uuid.uuid4(),
        session_id=session_id,
        role="assistant",
        content="Here are the top candidates",
        intent="top_candidates",
        entities={},
        confidence=0.9,
        sources=[],
        created_at=datetime.now(timezone.utc),
    )
    result = MagicMock()
    result.scalars.return_value.all.return_value = [listed]
    mock_db.execute = AsyncMock(return_value=result)

    messages = await get_session_messages(mock_db, session_id)

    assert len(messages) == 1
    assert messages[0].role == "assistant"
