import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.crud.candidate import create_candidate, update_candidate
from app.crud.job import create_job, delete_job, get_job_by_id, update_job
from app.crud.match import (
    batch_auto_score_job_matches,
    calculate_match_score,
    get_matches_by_candidate,
    get_matches_by_job,
    get_top_candidates,
    get_top_jobs,
    upsert_match_score,
)
from app.crud.user import create_user, deactivate_user, get_user_by_id, list_users, update_user
from app.models.job import Job, JobStatus
from app.models.match import MatchScore
from app.models.user import User, UserRole
from app.schemas.candidate import CandidateCreate, CandidateSkillInput, CandidateUpdate
from app.schemas.job import JobCreate, JobSkillInput, JobUpdate
from app.schemas.user import UserCreate, UserUpdate


@pytest.mark.asyncio
async def test_job_crud_validation_and_skills() -> None:
    mock_db = AsyncMock()
    skill_id = uuid.uuid4()
    duplicate_skill = JobSkillInput(skill_id=skill_id, weight=1.0)
    payload = JobCreate(
        title="Engineer",
        skills=[duplicate_skill, duplicate_skill],
    )
    with pytest.raises(HTTPException) as dup_exc:
        await create_job(mock_db, payload, owner_id=uuid.uuid4())
    assert dup_exc.value.detail == "Duplicate skill IDs in request"

    skill_lookup = MagicMock()
    skill_lookup.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=skill_lookup)
    payload_one = JobCreate(title="Engineer", skills=[JobSkillInput(skill_id=skill_id)])
    with pytest.raises(HTTPException) as missing_exc:
        await create_job(mock_db, payload_one, owner_id=uuid.uuid4())
    assert "skills not found" in missing_exc.value.detail

    job_id = uuid.uuid4()
    job = Job(
        id=job_id,
        title="Engineer",
        description=None,
        owner_id=uuid.uuid4(),
        status=JobStatus.OPEN.value,
    )
    job.skills = []
    lookup = MagicMock()
    lookup.scalar_one_or_none.return_value = job
    mock_db.execute = AsyncMock(return_value=lookup)
    mock_db.delete = AsyncMock()
    mock_db.commit = AsyncMock()

    with patch("app.crud.job._replace_job_skills", new_callable=AsyncMock):
        updated = await update_job(
            mock_db,
            job_id,
            JobUpdate(title="Senior Engineer", description="APIs", skills=[]),
        )
    assert updated.title == "Senior Engineer"
    await delete_job(mock_db, job_id)
    mock_db.delete.assert_awaited_once()

    missing_lookup = MagicMock()
    missing_lookup.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=missing_lookup)
    with pytest.raises(HTTPException) as not_found:
        await get_job_by_id(mock_db, job_id)
    assert not_found.value.status_code == 404


@pytest.mark.asyncio
async def test_candidate_create_with_skills_and_update_skills() -> None:
    skill_id = uuid.uuid4()
    mock_db = AsyncMock()
    skill_lookup = MagicMock()
    skill_lookup.scalars.return_value.all.return_value = [skill_id]
    mock_db.execute = AsyncMock(return_value=skill_lookup)
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    payload = CandidateCreate(
        full_name="Jane",
        email="jane@example.com",
        skills=[CandidateSkillInput(skill_id=skill_id, level="senior")],
    )
    created = await create_candidate(mock_db, payload)
    assert created.full_name == "Jane"

    from app.models.candidate import Candidate

    candidate_id = uuid.uuid4()
    candidate = Candidate(
        id=candidate_id,
        full_name="Jane",
        email="jane@example.com",
        resume_path=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    candidate.skill_links = []
    lookup = MagicMock()
    lookup.scalar_one_or_none.return_value = candidate
    mock_db.execute = AsyncMock(return_value=skill_lookup)

    with patch("app.crud.candidate.get_candidate_by_id", new_callable=AsyncMock, return_value=candidate):
        updated = await update_candidate(
            mock_db,
            candidate_id,
            CandidateUpdate(skills=[CandidateSkillInput(skill_id=skill_id)]),
        )
    assert updated.full_name == "Jane"


@pytest.mark.asyncio
async def test_match_crud_paths() -> None:
    candidate_id = uuid.uuid4()
    job_id = uuid.uuid4()
    mock_db = AsyncMock()

    with patch("app.crud.match._validate_candidate_exists", new_callable=AsyncMock), patch(
        "app.crud.match._validate_job_exists", new_callable=AsyncMock
    ), patch("app.crud.match.MatchEngine") as engine_cls:
        engine = engine_cls.return_value
        engine.calculate_match_score = AsyncMock(return_value=(80.0, {"final_score": 80.0}))
        score, explanation = await calculate_match_score(mock_db, candidate_id, job_id)
    assert score == 80.0
    assert explanation["final_score"] == 80.0

    match = MatchScore(
        id=uuid.uuid4(),
        candidate_id=candidate_id,
        job_id=job_id,
        score=80.0,
        explanation={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    upsert_result = MagicMock()
    upsert_result.fetchone.return_value = (match,)
    mock_db.execute = AsyncMock(return_value=upsert_result)
    mock_db.commit = AsyncMock()

    with patch("app.crud.match._validate_candidate_exists", new_callable=AsyncMock), patch(
        "app.crud.match._validate_job_exists", new_callable=AsyncMock
    ):
        stored = await upsert_match_score(mock_db, candidate_id, job_id, 80.0, {})
    assert stored.score == 80.0

    upsert_result.fetchone.return_value = None
    with patch("app.crud.match._validate_candidate_exists", new_callable=AsyncMock), patch(
        "app.crud.match._validate_job_exists", new_callable=AsyncMock
    ):
        with pytest.raises(HTTPException) as upsert_fail:
            await upsert_match_score(mock_db, candidate_id, job_id, 80.0, {})
    assert upsert_fail.value.status_code == 500

    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = [match]
    mock_db.execute = AsyncMock(return_value=list_result)

    with patch("app.crud.match._validate_job_exists", new_callable=AsyncMock):
        by_job = await get_matches_by_job(mock_db, job_id)
    with patch("app.crud.match._validate_candidate_exists", new_callable=AsyncMock):
        by_candidate = await get_matches_by_candidate(mock_db, candidate_id)
        top_jobs = await get_top_jobs(mock_db, candidate_id, limit=1)
    with patch("app.crud.match._validate_job_exists", new_callable=AsyncMock):
        top_candidates = await get_top_candidates(mock_db, job_id, limit=1)

    assert by_job == [match]
    assert by_candidate == [match]
    assert top_jobs == [match]
    assert top_candidates == [match]

    with patch("app.crud.match._validate_job_exists", new_callable=AsyncMock), patch(
        "app.crud.match.MatchEngine"
    ) as engine_cls, patch(
        "app.crud.match.upsert_match_score",
        new_callable=AsyncMock,
        return_value=match,
    ):
        engine_cls.return_value.calculate_match_score = AsyncMock(
            return_value=(75.0, {"final_score": 75.0})
        )
        all_candidates = MagicMock()
        all_candidates.all.return_value = [(candidate_id,)]
        mock_db.execute = AsyncMock(return_value=all_candidates)
        batch = await batch_auto_score_job_matches(mock_db, job_id)
    assert batch.scored_count == 1


@pytest.mark.asyncio
async def test_user_crud_operations() -> None:
    mock_db = AsyncMock()
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        full_name="Admin",
        email="admin@example.com",
        hashed_password="hash",
        role=UserRole.Admin,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    existing = MagicMock()
    existing.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=existing)
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    created = await create_user(
        mock_db,
        UserCreate(
            full_name="Admin",
            email="new@example.com",
            password="Password1",
            role=UserRole.Admin,
        ),
    )
    assert created.email == "new@example.com"

    existing.scalar_one_or_none.return_value = user
    with pytest.raises(HTTPException) as dup_email:
        await create_user(
            mock_db,
            UserCreate(
                full_name="Other",
                email="admin@example.com",
                password="Password1",
            ),
        )
    assert dup_email.value.status_code == 400

    lookup = MagicMock()
    lookup.scalar_one_or_none.return_value = user
    mock_db.execute = AsyncMock(return_value=lookup)
    listed = MagicMock()
    listed.scalars.return_value.all.return_value = [user]
    mock_db.execute = AsyncMock(side_effect=[listed, lookup, lookup])

    users = await list_users(mock_db)
    assert users[0].id == user_id

    updated = await update_user(
        mock_db,
        user_id,
        UserUpdate(full_name="Super Admin", password="Newpass1", role=UserRole.Admin, is_active=True),
    )
    assert updated.full_name == "Super Admin"

    deactivated = await deactivate_user(mock_db, user_id)
    assert deactivated.is_active is False

    lookup.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=lookup)
    with pytest.raises(HTTPException) as missing:
        await get_user_by_id(mock_db, uuid.uuid4())
    assert missing.value.status_code == 404
