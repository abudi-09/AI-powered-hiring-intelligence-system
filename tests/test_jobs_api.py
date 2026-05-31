import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token, get_password_hash
from app.db.session import get_db
from app.main import create_app
from app.models.job import Job, JobStatus
from app.models.user import User, UserRole
from app.schemas.job import JobRead


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
async def jobs_client(recruiter_user: User):
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


def _job_read(job_id: uuid.UUID) -> JobRead:
    now = datetime.now(timezone.utc)
    return JobRead(
        id=job_id,
        title="Backend Engineer",
        description="Build APIs",
        status=JobStatus.OPEN,
        owner_id=uuid.uuid4(),
        skills=[],
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_list_jobs_returns_paginated_response(jobs_client) -> None:
    client, token, _ = jobs_client
    job = Job(
        id=uuid.uuid4(),
        title="Backend Engineer",
        description="Build APIs",
        status=JobStatus.OPEN.value,
        owner_id=uuid.uuid4(),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    with patch(
        "app.api.jobs.crud_list_jobs",
        new_callable=AsyncMock,
        return_value=([job], 1),
    ), patch(
        "app.api.jobs._job_to_read",
        new_callable=AsyncMock,
        return_value=_job_read(job.id),
    ):
        response = await client.get(
            "/jobs/?skip=0&limit=10&status=open",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "Backend Engineer"


@pytest.mark.asyncio
async def test_create_job_returns_created_row(jobs_client, recruiter_user: User) -> None:
    client, token, _ = jobs_client
    job_id = uuid.uuid4()
    job = Job(
        id=job_id,
        title="Data Engineer",
        description="Pipelines",
        status=JobStatus.DRAFT.value,
        owner_id=recruiter_user.id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    with patch(
        "app.api.jobs.crud_create_job",
        new_callable=AsyncMock,
        return_value=job,
    ), patch(
        "app.api.jobs._job_to_read",
        new_callable=AsyncMock,
        return_value=_job_read(job_id),
    ):
        response = await client.post(
            "/jobs/",
            headers={"Authorization": f"Bearer {token}"},
            json={"title": "Data Engineer", "description": "Pipelines", "status": "draft", "skills": []},
        )

    assert response.status_code == 201
    assert response.json()["title"] == "Backend Engineer"


@pytest.mark.asyncio
async def test_get_update_and_delete_job_routes(jobs_client) -> None:
    client, token, _ = jobs_client
    job_id = uuid.uuid4()
    job = Job(
        id=job_id,
        title="SRE",
        description="Ops",
        status=JobStatus.OPEN.value,
        owner_id=uuid.uuid4(),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    job_read = _job_read(job_id)

    with patch("app.api.jobs.crud_get_job_by_id", new_callable=AsyncMock, return_value=job), patch(
        "app.api.jobs.crud_update_job", new_callable=AsyncMock, return_value=job
    ), patch("app.api.jobs.crud_delete_job", new_callable=AsyncMock), patch(
        "app.api.jobs._job_to_read", new_callable=AsyncMock, return_value=job_read
    ):
        get_response = await client.get(
            f"/jobs/{job_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        patch_response = await client.patch(
            f"/jobs/{job_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"title": "Senior SRE"},
        )
        delete_response = await client.delete(
            f"/jobs/{job_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert get_response.status_code == 200
    assert patch_response.status_code == 200
    assert delete_response.status_code == 204


@pytest.mark.asyncio
async def test_jobs_routes_require_authentication() -> None:
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/jobs/")

    assert response.status_code == 401
