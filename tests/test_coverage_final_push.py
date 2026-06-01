import io
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, UploadFile
from httpx import ASGITransport, AsyncClient

from app.api import candidates as candidates_api
from app.api import jobs as jobs_api
from app.api.deps import get_current_user
from app.core.security import create_access_token, decode_access_token, get_password_hash
from app.crud.candidate import _validate_skills_exist, merge_candidate_skills
from app.crud.job import _validate_skills_exist as validate_job_skills, list_jobs
from app.crud.skill import update_skill
from app.db.session import get_db
from app.main import create_app
from app.models.candidate import Candidate
from app.models.job import Job, JobStatus
from app.models.skill import Skill
from app.models.user import User, UserRole
from app.schemas.candidate import CandidateRead
from app.schemas.skill import SkillUpdate
from app.services import intelligence_metrics as metrics
from app.services.conversation_orchestrator import ConversationOrchestrator
from app.services.analytics_engine import AnalyticsEngine
from app.services.insight_engine import InsightEngine
from app.services.match_engine import MatchEngine
from app.services.scoring import level_multiplier
from tests.helpers.mock_db import all_result, mock_async_session


def test_intelligence_metrics_branches() -> None:
    assert metrics.level_to_score("senior") == 80.0
    assert metrics.level_to_score(None) == 50.0
    assert metrics.hiring_difficulty_score(avg_match_score=40.0, candidates_with_matches=2, required_skills_count=12) == 95.0
    assert metrics.skill_scarcity_index(demand=0, supply=0) == 0.0
    assert metrics.skill_scarcity_index(demand=3, supply=0) == 100.0
    assert metrics.candidate_market_competitiveness([]) == (0.0, 0)
    score, tops = metrics.candidate_market_competitiveness([90.0, 85.0, 82.0, 81.0, 80.0, 70.0])
    assert tops == 5
    versatility, _, _ = metrics.candidate_versatility_index(["senior"] * 16)
    assert versatility >= 80.0
    growth = metrics.growth_potential_score(
        versatility_index=70.0,
        skill_depth_score=75.0,
        max_years_experience=3.0,
    )
    assert growth >= 70.0


def test_level_multiplier_unknown_level() -> None:
    assert level_multiplier("staff") == 1.0


@pytest.mark.asyncio
async def test_match_engine_loads_skill_rows() -> None:
    job_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    skill_id = uuid.uuid4()
    db = mock_async_session(
        [
            all_result([(skill_id, "Python", 1.0)]),
            all_result([(skill_id, "Python", "senior", 5.0)]),
        ]
    )
    engine = MatchEngine(db)
    score, explanation = await engine.calculate_match_score(candidate_id, job_id)
    assert score >= 0.0
    assert "final_score" in explanation


@pytest.mark.asyncio
async def test_orchestrator_generic_fetch_branches() -> None:
    candidate_id = uuid.uuid4()
    orchestrator = ConversationOrchestrator(AsyncMock())
    with patch.object(
        orchestrator.analytics,
        "compute_candidate_analytics",
        new_callable=AsyncMock,
        return_value={"average_score": 60.0},
    ), patch.object(
        orchestrator.insight_engine,
        "generate_candidate_insights",
        new_callable=AsyncMock,
        return_value=[{"title": "Strength"}],
    ):
        plan = {
            "intent": "candidate_analysis",
            "steps": ["fetch_analytics", "fetch_insights"],
            "entities": {"entity_id": str(candidate_id), "entity_type": "candidate"},
        }
        result = await orchestrator.execute_plan(plan)
    assert result["analytics"]["average_score"] == 60.0
    assert result["insights"][0]["title"] == "Strength"


@pytest.mark.asyncio
async def test_job_to_read_maps_skills() -> None:
    job_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    job = Job(
        id=job_id,
        title="Engineer",
        description="APIs",
        owner_id=uuid.uuid4(),
        status=JobStatus.OPEN.value,
        created_at=now,
        updated_at=now,
    )
    skill_id = uuid.uuid4()
    db = mock_async_session([all_result([(skill_id, "Python", 0.8)])])
    read = await jobs_api._job_to_read(db, job)
    assert read.skills[0].skill_name == "Python"


@pytest.mark.asyncio
async def test_candidate_helpers_and_crud_edges() -> None:
    mock_db = AsyncMock()
    duplicate_id = uuid.uuid4()
    with pytest.raises(HTTPException) as dup_exc:
        await _validate_skills_exist(mock_db, [duplicate_id, duplicate_id])
    assert dup_exc.value.detail == "Duplicate skill IDs in request"

    candidate = Candidate(
        id=uuid.uuid4(),
        full_name="Jane",
        email="jane@example.com",
        resume_path=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    candidate.skill_links = []
    await merge_candidate_skills(mock_db, candidate, [])
    assert candidate.skill_links == []

    name = candidates_api._safe_resume_filename("resume.pdf", candidate.id)
    assert name.endswith(".pdf")


@pytest.mark.asyncio
async def test_job_list_search_and_empty_skill_validation() -> None:
    await validate_job_skills(AsyncMock(), [])
    job = Job(
        id=uuid.uuid4(),
        title="Data",
        description=None,
        owner_id=uuid.uuid4(),
        status=JobStatus.OPEN.value,
    )
    mock_db = AsyncMock()
    count_result = MagicMock()
    count_result.scalar_one.return_value = 1
    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = [job]
    mock_db.execute = AsyncMock(side_effect=[count_result, list_result])
    jobs, total = await list_jobs(mock_db, q="Data")
    assert total == 1
    assert jobs[0].title == "Data"


@pytest.mark.asyncio
async def test_insight_engine_moderate_and_low_difficulty() -> None:
    job_id = uuid.uuid4()
    analytics = {
        "hiring_difficulty_score": 55.0,
        "average_match_score": 60.0,
        "candidate_count": 0,
        "top_candidate_score": None,
    }
    with patch.object(
        AnalyticsEngine,
        "compute_job_analytics",
        new_callable=AsyncMock,
        return_value=analytics,
    ), patch.object(
        AnalyticsEngine,
        "compute_skill_demand",
        new_callable=AsyncMock,
        return_value=[],
    ):
        engine = InsightEngine(AsyncMock())
        insights = await engine.generate_job_insights(job_id)
    severities = {item["severity"] for item in insights}
    assert "medium" in severities or "high" in severities

    low_analytics = {
        "hiring_difficulty_score": 20.0,
        "average_match_score": 85.0,
        "candidate_count": 5,
        "top_candidate_score": 90.0,
    }
    with patch.object(
        AnalyticsEngine,
        "compute_job_analytics",
        new_callable=AsyncMock,
        return_value=low_analytics,
    ), patch.object(
        AnalyticsEngine,
        "compute_skill_demand",
        new_callable=AsyncMock,
        return_value=[],
    ), patch(
        "app.services.insight_engine.get_top_candidates",
        new_callable=AsyncMock,
        return_value=[],
    ):
        engine = InsightEngine(AsyncMock())
        low_insights = await engine.generate_job_insights(job_id)
    assert any(item["insight_type"] == "hiring_opportunity" for item in low_insights)


@pytest.mark.asyncio
async def test_skill_update_duplicate_name_rejected() -> None:
    skill_id = uuid.uuid4()
    skill = Skill(id=skill_id, name="Python", category="Lang", created_at=datetime.now(timezone.utc))
    mock_db = AsyncMock()
    lookup = MagicMock()
    lookup.scalar_one_or_none.return_value = skill
    existing = MagicMock()
    existing.scalar_one_or_none.return_value = uuid.uuid4()
    mock_db.execute = AsyncMock(side_effect=[lookup, existing])

    with pytest.raises(HTTPException) as exc:
        await update_skill(mock_db, skill_id, SkillUpdate(name="python"))
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_get_current_user_missing_subject() -> None:
    user_id = uuid.uuid4()
    token = create_access_token(subject=str(user_id), role=UserRole.Recruiter.value)
    payload = decode_access_token(token)
    payload.pop("sub")
    broken = __import__("jose").jwt.encode(
        payload,
        __import__("app.core.config", fromlist=["settings"]).settings.jwt_secret_key.get_secret_value(),
        algorithm="HS256",
    )
    with pytest.raises(HTTPException) as exc:
        await get_current_user(db=AsyncMock(), token=broken)
    assert exc.value.status_code == 401


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


@pytest.mark.asyncio
async def test_chat_session_and_recommendation_delete_success(recruiter_user: User) -> None:
    mock_session = AsyncMock()
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = recruiter_user
    mock_session.execute = AsyncMock(return_value=user_result)

    app = create_app()

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db
    token = create_access_token(subject=str(recruiter_user.id), role=recruiter_user.role.value)
    session_id = uuid.uuid4()

    with patch(
        "app.api.chat.conversation_crud.get_session",
        new_callable=AsyncMock,
        return_value=None,
    ), patch(
        "app.api.chat.conversation_crud.delete_session",
        new_callable=AsyncMock,
        return_value=True,
    ), patch(
        "app.api.recommendations.recommendation_crud.delete_recommendation",
        new_callable=AsyncMock,
        return_value=True,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            missing_session = await client.get(
                f"/chat/session/{session_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            deleted_session = await client.delete(
                f"/chat/session/{session_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            deleted_rec = await client.delete(
                f"/recommendations/{uuid.uuid4()}",
                headers={"Authorization": f"Bearer {token}"},
            )

    app.dependency_overrides.clear()
    assert missing_session.status_code == 404
    assert deleted_session.status_code == 200
    assert deleted_rec.status_code == 200


@pytest.mark.asyncio
async def test_extract_resume_empty_and_unicode_errors(recruiter_user: User, tmp_path) -> None:
    candidate_id = uuid.uuid4()
    candidate = Candidate(
        id=candidate_id,
        full_name="Jane",
        email="jane@example.com",
        resume_path=f"{candidate_id}/resume.txt",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    resume_file = tmp_path / str(candidate_id) / "resume.txt"
    resume_file.parent.mkdir(parents=True, exist_ok=True)
    resume_file.write_text("plain text resume", encoding="utf-8")

    def _auth():
        r = MagicMock()
        r.scalar_one_or_none.return_value = recruiter_user
        return r

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(side_effect=[_auth(), all_result([])])
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    app = create_app()

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db
    token = create_access_token(subject=str(recruiter_user.id), role=recruiter_user.role.value)

    with patch.object(candidates_api.settings, "resume_storage_path", tmp_path), patch(
        "app.api.candidates.crud_get_candidate_by_id",
        new_callable=AsyncMock,
        return_value=candidate,
    ), patch(
        "app.api.candidates.SkillExtractor.extract_from_text",
        return_value=[],
    ), patch(
        "app.api.candidates._candidate_to_read",
        new_callable=AsyncMock,
        return_value=CandidateRead(
            id=candidate_id,
            full_name="Jane",
            email="jane@example.com",
            resume_path=candidate.resume_path,
            skills=[],
            created_at=candidate.created_at,
            updated_at=candidate.updated_at,
        ),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            empty_extract = await client.post(
                f"/candidates/{candidate_id}/skills/extract-from-resume",
                headers={"Authorization": f"Bearer {token}"},
            )

    app.dependency_overrides.clear()
    assert empty_extract.status_code == 200
    assert empty_extract.json()["extracted_count"] == 0

    mock_session.execute = AsyncMock(side_effect=[_auth()])
    app.dependency_overrides[get_db] = override_get_db
    with patch.object(candidates_api.settings, "resume_storage_path", tmp_path), patch(
        "app.api.candidates.crud_get_candidate_by_id",
        new_callable=AsyncMock,
        return_value=candidate,
    ), patch(
        "app.api.candidates._read_resume_text",
        side_effect=UnicodeDecodeError("utf-8", b"", 0, 1, "invalid"),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            bad_encoding = await client.post(
                f"/candidates/{candidate_id}/skills/extract-from-resume",
                headers={"Authorization": f"Bearer {token}"},
            )
    app.dependency_overrides.clear()
    assert bad_encoding.status_code == 400
