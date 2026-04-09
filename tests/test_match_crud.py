import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.crud.match import upsert_match_score
from app.models.match import MatchScore


@pytest.mark.asyncio
async def test_upsert_match_score_updates_timestamp_on_conflict() -> None:
    candidate_id = uuid.uuid4()
    job_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    match = MatchScore(
        id=uuid.uuid4(),
        candidate_id=candidate_id,
        job_id=job_id,
        score=80.0,
        explanation={"final_score": 80.0},
        created_at=now,
        updated_at=now,
    )

    mock_db = AsyncMock()
    candidate_lookup = MagicMock()
    candidate_lookup.scalar_one_or_none.return_value = candidate_id
    job_lookup = MagicMock()
    job_lookup.scalar_one_or_none.return_value = job_id
    mock_db.execute = AsyncMock(
        side_effect=[
            candidate_lookup,
            job_lookup,
            MagicMock(fetchone=MagicMock(return_value=(match,))),
        ]
    )

    result = await upsert_match_score(
        mock_db,
        candidate_id,
        job_id,
        80.0,
        {"final_score": 80.0},
    )

    assert result.score == 80.0
    assert mock_db.execute.await_count == 3
