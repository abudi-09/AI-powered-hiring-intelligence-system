import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.crud.match import BatchAutoScoreResult, batch_auto_score_job_matches
from app.models.match import MatchScore


def _match_row(
    candidate_id: uuid.UUID,
    job_id: uuid.UUID,
    score: float,
) -> MatchScore:
    now = datetime.now(timezone.utc)
    return MatchScore(
        id=uuid.uuid4(),
        candidate_id=candidate_id,
        job_id=job_id,
        score=score,
        explanation={"final_score": score},
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_batch_auto_score_scores_all_candidates() -> None:
    job_id = uuid.uuid4()
    candidate_a = uuid.uuid4()
    candidate_b = uuid.uuid4()
    mock_db = AsyncMock()

    job_result = MagicMock()
    job_result.scalar_one_or_none.return_value = job_id

    candidates_result = MagicMock()
    candidates_result.all.return_value = [(candidate_a,), (candidate_b,)]

    mock_db.execute = AsyncMock(side_effect=[job_result, candidates_result])

    match_a = _match_row(candidate_a, job_id, 88.0)
    match_b = _match_row(candidate_b, job_id, 62.0)

    with patch(
        "app.crud.match.MatchEngine.calculate_match_score",
        new_callable=AsyncMock,
        side_effect=[(88.0, {"final_score": 88.0}), (62.0, {"final_score": 62.0})],
    ):
        with patch(
            "app.crud.match.upsert_match_score",
            new_callable=AsyncMock,
            side_effect=[match_b, match_a],
        ) as upsert:
            result = await batch_auto_score_job_matches(mock_db, job_id)

    assert len(result.matches) == 2
    assert [match.score for match in result.matches] == [88.0, 62.0]
    assert result.scored_count == 2
    assert result.skipped_count == 0
    assert result.total_candidates == 2
    assert upsert.await_count == 2
    upsert.assert_any_await(
        mock_db,
        candidate_a,
        job_id,
        88.0,
        {"final_score": 88.0},
        commit=False,
        validate=False,
    )
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_batch_auto_score_filters_requested_candidates() -> None:
    job_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    mock_db = AsyncMock()

    job_result = MagicMock()
    job_result.scalar_one_or_none.return_value = job_id

    existing_result = MagicMock()
    existing_result.scalars.return_value.all.return_value = [candidate_id]

    mock_db.execute = AsyncMock(side_effect=[job_result, existing_result])

    match = _match_row(candidate_id, job_id, 75.0)

    with patch(
        "app.crud.match.MatchEngine.calculate_match_score",
        new_callable=AsyncMock,
        return_value=(75.0, {"final_score": 75.0}),
    ):
        with patch(
            "app.crud.match.upsert_match_score",
            new_callable=AsyncMock,
            return_value=match,
        ):
            result = await batch_auto_score_job_matches(
                mock_db,
                job_id,
                candidate_ids=[candidate_id],
            )

    assert len(result.matches) == 1
    assert result.matches[0].candidate_id == candidate_id


@pytest.mark.asyncio
async def test_batch_auto_score_returns_empty_when_no_candidates() -> None:
    job_id = uuid.uuid4()
    mock_db = AsyncMock()

    job_result = MagicMock()
    job_result.scalar_one_or_none.return_value = job_id

    candidates_result = MagicMock()
    candidates_result.all.return_value = []

    mock_db.execute = AsyncMock(side_effect=[job_result, candidates_result])

    result = await batch_auto_score_job_matches(mock_db, job_id)

    assert result.matches == []
    assert result.scored_count == 0
    mock_db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_batch_auto_score_skips_duplicate_candidate_ids() -> None:
    job_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    mock_db = AsyncMock()

    job_result = MagicMock()
    job_result.scalar_one_or_none.return_value = job_id

    existing_result = MagicMock()
    existing_result.scalars.return_value.all.return_value = [candidate_id]

    mock_db.execute = AsyncMock(side_effect=[job_result, existing_result])

    match = _match_row(candidate_id, job_id, 75.0)

    with patch(
        "app.crud.match.MatchEngine.calculate_match_score",
        new_callable=AsyncMock,
        return_value=(75.0, {"final_score": 75.0}),
    ):
        with patch(
            "app.crud.match.upsert_match_score",
            new_callable=AsyncMock,
            return_value=match,
        ):
            result = await batch_auto_score_job_matches(
                mock_db,
                job_id,
                candidate_ids=[candidate_id, candidate_id],
            )

    assert result.scored_count == 1
    assert result.skipped_count == 1
    assert result.total_candidates == 2


@pytest.mark.asyncio
async def test_batch_auto_score_rejects_missing_job() -> None:
    job_id = uuid.uuid4()
    mock_db = AsyncMock()

    job_result = MagicMock()
    job_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=job_result)

    with pytest.raises(HTTPException) as exc:
        await batch_auto_score_job_matches(mock_db, job_id)

    assert exc.value.status_code == 404
    assert exc.value.detail == "Job not found"


@pytest.mark.asyncio
async def test_batch_auto_score_rejects_missing_candidate_filter() -> None:
    job_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    mock_db = AsyncMock()

    job_result = MagicMock()
    job_result.scalar_one_or_none.return_value = job_id

    existing_result = MagicMock()
    existing_result.scalars.return_value.all.return_value = []

    mock_db.execute = AsyncMock(side_effect=[job_result, existing_result])

    with pytest.raises(HTTPException) as exc:
        await batch_auto_score_job_matches(
            mock_db,
            job_id,
            candidate_ids=[candidate_id],
        )

    assert exc.value.status_code == 404
    assert exc.value.detail == "One or more candidates not found"
