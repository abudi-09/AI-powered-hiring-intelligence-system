import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.crud.candidate import (
    create_candidate,
    delete_candidate,
    get_candidate_by_id,
    list_candidates,
    merge_candidate_skills,
    update_candidate,
)
from app.models.candidate import Candidate
from app.models.candidate_skill import CandidateSkill
from app.schemas.candidate import CandidateCreate, CandidateSkillInput, CandidateUpdate


def _candidate(candidate_id: uuid.UUID | None = None) -> Candidate:
    return Candidate(
        id=candidate_id or uuid.uuid4(),
        full_name="Jane Doe",
        email="jane@example.com",
        resume_path=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_get_candidate_by_id_raises_404_when_missing() -> None:
    mock_db = AsyncMock()
    lookup = MagicMock()
    lookup.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=lookup)

    with pytest.raises(HTTPException) as exc:
        await get_candidate_by_id(mock_db, uuid.uuid4())

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_list_candidates_returns_rows_and_total() -> None:
    candidate = _candidate()
    mock_db = AsyncMock()
    count_lookup = MagicMock()
    count_lookup.scalar_one.return_value = 1
    list_lookup = MagicMock()
    list_lookup.scalars.return_value.all.return_value = [candidate]
    mock_db.execute = AsyncMock(side_effect=[count_lookup, list_lookup])

    rows, total = await list_candidates(mock_db, skip=0, limit=10, q="Jane")

    assert total == 1
    assert rows[0].full_name == "Jane Doe"


@pytest.mark.asyncio
async def test_create_candidate_persists_without_skills() -> None:
    mock_db = AsyncMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    mock_db.add = MagicMock()

    payload = CandidateCreate(full_name="New Hire", email="new@example.com", skills=[])

    result = await create_candidate(mock_db, payload)

    assert result.full_name == "New Hire"
    mock_db.add.assert_called_once()
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_candidate_rejects_unknown_skill_ids() -> None:
    skill_id = uuid.uuid4()
    mock_db = AsyncMock()
    skill_lookup = MagicMock()
    skill_lookup.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=skill_lookup)

    payload = CandidateCreate(
        full_name="New Hire",
        email="new@example.com",
        skills=[CandidateSkillInput(skill_id=skill_id, level="intermediate")],
    )

    with pytest.raises(HTTPException) as exc:
        await create_candidate(mock_db, payload)

    assert exc.value.status_code == 400
    assert exc.value.detail == "One or more skills not found"


@pytest.mark.asyncio
async def test_update_candidate_applies_field_changes() -> None:
    candidate_id = uuid.uuid4()
    candidate = _candidate(candidate_id)
    mock_db = AsyncMock()
    lookup = MagicMock()
    lookup.scalar_one_or_none.return_value = candidate
    mock_db.execute = AsyncMock(return_value=lookup)
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    result = await update_candidate(
        mock_db,
        candidate_id,
        CandidateUpdate(full_name="Updated Name"),
    )

    assert result.full_name == "Updated Name"
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_candidate_removes_row() -> None:
    candidate_id = uuid.uuid4()
    candidate = _candidate(candidate_id)
    mock_db = AsyncMock()
    lookup = MagicMock()
    lookup.scalar_one_or_none.return_value = candidate
    mock_db.execute = AsyncMock(return_value=lookup)
    mock_db.delete = AsyncMock()
    mock_db.commit = AsyncMock()

    await delete_candidate(mock_db, candidate_id)

    mock_db.delete.assert_awaited_once_with(candidate)
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_merge_candidate_skills_adds_new_link() -> None:
    candidate = _candidate()
    candidate.skill_links = []
    skill_id = uuid.uuid4()
    mock_db = AsyncMock()
    skill_lookup = MagicMock()
    skill_lookup.scalars.return_value.all.return_value = [skill_id]
    mock_db.execute = AsyncMock(return_value=skill_lookup)

    await merge_candidate_skills(
        mock_db,
        candidate,
        [{"skill_id": skill_id, "level": "senior", "years_experience": 5}],
    )

    assert len(candidate.skill_links) == 1
    assert candidate.skill_links[0].skill_id == skill_id
    assert candidate.skill_links[0].level == "senior"


@pytest.mark.asyncio
async def test_merge_candidate_skills_updates_existing_link() -> None:
    skill_id = uuid.uuid4()
    candidate = _candidate()
    existing = CandidateSkill(
        candidate_id=candidate.id,
        skill_id=skill_id,
        level="junior",
        years_experience=1,
    )
    candidate.skill_links = [existing]
    mock_db = AsyncMock()
    skill_lookup = MagicMock()
    skill_lookup.scalars.return_value.all.return_value = [skill_id]
    mock_db.execute = AsyncMock(return_value=skill_lookup)

    await merge_candidate_skills(
        mock_db,
        candidate,
        [{"skill_id": skill_id, "level": "senior", "years_experience": 6}],
    )

    assert len(candidate.skill_links) == 1
    assert candidate.skill_links[0].level == "senior"
    assert candidate.skill_links[0].years_experience == 6
