import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.crud.candidate import create_candidate
from app.crud.job import create_job
from app.crud.match import get_matches_by_candidate, get_matches_by_job, get_top_jobs
from app.schemas.candidate import CandidateCreate
from app.schemas.candidate_skill import CandidateSkillInput
from app.schemas.job import JobCreate, JobSkillInput


@pytest.mark.asyncio
async def test_create_candidate_rejects_missing_skills() -> None:
    skill_id = uuid.uuid4()
    payload = CandidateCreate(
        full_name="Jane Doe",
        skills=[CandidateSkillInput(skill_id=skill_id)],
    )
    mock_db = AsyncMock()
    lookup = MagicMock()
    lookup.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=lookup)

    with pytest.raises(HTTPException) as exc:
        await create_candidate(mock_db, payload)

    assert exc.value.status_code == 400
    assert exc.value.detail == "One or more skills not found"


@pytest.mark.asyncio
async def test_create_candidate_rejects_duplicate_skill_ids() -> None:
    skill_id = uuid.uuid4()
    payload = CandidateCreate(
        full_name="Jane Doe",
        skills=[
            CandidateSkillInput(skill_id=skill_id),
            CandidateSkillInput(skill_id=skill_id),
        ],
    )
    mock_db = AsyncMock()

    with pytest.raises(HTTPException) as exc:
        await create_candidate(mock_db, payload)

    assert exc.value.status_code == 400
    assert exc.value.detail == "Duplicate skill IDs in request"
    mock_db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_job_rejects_duplicate_skill_ids() -> None:
    skill_id = uuid.uuid4()
    payload = JobCreate(
        title="Backend Engineer",
        skills=[
            JobSkillInput(skill_id=skill_id, weight=1.0),
            JobSkillInput(skill_id=skill_id, weight=0.5),
        ],
    )
    mock_db = AsyncMock()

    with pytest.raises(HTTPException) as exc:
        await create_job(mock_db, payload, owner_id=uuid.uuid4())

    assert exc.value.status_code == 400
    assert exc.value.detail == "Duplicate skill IDs in request"


@pytest.mark.asyncio
async def test_get_matches_by_job_rejects_unknown_job() -> None:
    job_id = uuid.uuid4()
    mock_db = AsyncMock()
    job_lookup = MagicMock()
    job_lookup.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=job_lookup)

    with pytest.raises(HTTPException) as exc:
        await get_matches_by_job(mock_db, job_id)

    assert exc.value.status_code == 404
    assert exc.value.detail == "Job not found"


@pytest.mark.asyncio
async def test_get_matches_by_candidate_rejects_unknown_candidate() -> None:
    candidate_id = uuid.uuid4()
    mock_db = AsyncMock()
    candidate_lookup = MagicMock()
    candidate_lookup.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=candidate_lookup)

    with pytest.raises(HTTPException) as exc:
        await get_matches_by_candidate(mock_db, candidate_id)

    assert exc.value.status_code == 404
    assert exc.value.detail == "Candidate not found"


@pytest.mark.asyncio
async def test_get_top_jobs_rejects_unknown_candidate() -> None:
    candidate_id = uuid.uuid4()
    mock_db = AsyncMock()
    candidate_lookup = MagicMock()
    candidate_lookup.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=candidate_lookup)

    with pytest.raises(HTTPException) as exc:
        await get_top_jobs(mock_db, candidate_id)

    assert exc.value.status_code == 404
    assert exc.value.detail == "Candidate not found"
