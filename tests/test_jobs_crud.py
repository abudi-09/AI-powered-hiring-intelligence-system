import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.crud.job import create_job, list_jobs, update_job
from app.models.job import Job, JobStatus
from app.schemas.job import JobCreate, JobUpdate


@pytest.mark.asyncio
async def test_create_job_defaults_to_open_status() -> None:
    owner_id = uuid.uuid4()
    payload = JobCreate(title="Backend Engineer")
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    job = await create_job(mock_db, payload, owner_id=owner_id)

    assert job.title == "Backend Engineer"
    assert job.status == JobStatus.OPEN.value
    assert job.owner_id == owner_id


@pytest.mark.asyncio
async def test_list_jobs_filters_by_status() -> None:
    open_job = Job(
        id=uuid.uuid4(),
        title="Open role",
        description=None,
        owner_id=uuid.uuid4(),
        status=JobStatus.OPEN.value,
    )
    mock_db = AsyncMock()
    count_result = MagicMock()
    count_result.scalar_one.return_value = 1
    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = [open_job]
    mock_db.execute = AsyncMock(side_effect=[count_result, list_result])

    jobs, total = await list_jobs(mock_db, status=JobStatus.OPEN)

    assert total == 1
    assert len(jobs) == 1
    assert jobs[0].status == JobStatus.OPEN.value


@pytest.mark.asyncio
async def test_update_job_can_close_posting() -> None:
    job_id = uuid.uuid4()
    job = Job(
        id=job_id,
        title="Backend Engineer",
        description=None,
        owner_id=uuid.uuid4(),
        status=JobStatus.OPEN.value,
    )
    mock_db = AsyncMock()
    lookup = MagicMock()
    lookup.scalar_one_or_none.return_value = job
    mock_db.execute = AsyncMock(return_value=lookup)

    updated = await update_job(mock_db, job_id, JobUpdate(status=JobStatus.CLOSED))

    assert updated.status == JobStatus.CLOSED.value
    mock_db.commit.assert_awaited_once()
