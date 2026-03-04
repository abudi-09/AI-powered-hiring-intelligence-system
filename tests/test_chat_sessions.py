import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.crud.conversation import list_user_sessions
from app.models.conversation import ConversationSession


@pytest.mark.asyncio
async def test_list_user_sessions_returns_message_counts() -> None:
    user_id = uuid.uuid4()
    session_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    session = ConversationSession(
        id=session_id,
        user_id=user_id,
        title="Pipeline review",
        context={},
        created_at=now,
        updated_at=now,
    )

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.all.return_value = [(session, 4)]
    mock_db.execute = AsyncMock(return_value=mock_result)

    rows = await list_user_sessions(mock_db, user_id)

    assert len(rows) == 1
    listed_session, message_count = rows[0]
    assert listed_session.id == session_id
    assert message_count == 4
    mock_db.execute.assert_awaited_once()
