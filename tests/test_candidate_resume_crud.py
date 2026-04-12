import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.crud.candidate import set_candidate_resume_path
from app.models.candidate import Candidate


@pytest.mark.asyncio
async def test_set_candidate_resume_path_updates_candidate() -> None:
    candidate_id = uuid.uuid4()
    candidate = Candidate(
        id=candidate_id,
        full_name="Jane Doe",
        email="jane@example.com",
        resume_path=None,
    )
    mock_db = AsyncMock()
    lookup = MagicMock()
    lookup.scalar_one_or_none.return_value = candidate
    mock_db.execute = AsyncMock(return_value=lookup)

    result = await set_candidate_resume_path(
        mock_db,
        candidate_id,
        f"{candidate_id}/resume.txt",
    )

    assert result.resume_path == f"{candidate_id}/resume.txt"
    mock_db.commit.assert_awaited_once()
