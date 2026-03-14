import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token, get_password_hash
from app.db.session import get_db
from app.main import create_app
from app.models.candidate import Candidate
from app.models.user import User, UserRole


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
def candidate_id() -> uuid.UUID:
    return uuid.UUID("00000000-0000-4000-8000-000000000030")


@pytest.mark.asyncio
async def test_extract_skills_from_resume_merges_catalog_skills(
    recruiter_user: User,
    candidate_id: uuid.UUID,
) -> None:
    python_id = uuid.UUID("00000000-0000-4000-8000-000000000040")
    react_id = uuid.UUID("00000000-0000-4000-8000-000000000041")
    candidate = Candidate(
        id=candidate_id,
        full_name="Jane Doe",
        email="jane@example.com",
        resume_path=f"{candidate_id}/resume.txt",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    catalog_result = MagicMock()
    catalog_result.all.return_value = [
        (python_id, "Python"),
        (react_id, "React"),
    ]

    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = recruiter_user

    skills_join_result = MagicMock()
    skills_join_result.all.return_value = [
        (python_id, "Python", "senior", 6.0),
        (react_id, "React", None, 2.0),
    ]

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(
        side_effect=[user_result, catalog_result, skills_join_result]
    )
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    app = create_app()

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db
    token = create_access_token(subject=str(recruiter_user.id), role=recruiter_user.role.value)

    resume_text = """
    Skills:
    Senior Python (6 years), React (2 yrs)
    """

    with patch(
        "app.api.candidates.crud_get_candidate_by_id",
        new_callable=AsyncMock,
        return_value=candidate,
    ):
        with patch(
            "app.api.candidates.crud_merge_candidate_skills",
            new_callable=AsyncMock,
        ) as merge_skills:
            with patch.object(Path, "is_file", return_value=True):
                with patch(
                    "app.api.candidates._read_resume_text",
                    new_callable=AsyncMock,
                    return_value=resume_text,
                ):
                    transport = ASGITransport(app=app)
                    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
                        response = await client.post(
                            f"/candidates/{candidate_id}/skills/extract-from-resume",
                            headers={"Authorization": f"Bearer {token}"},
                        )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["extracted_count"] == 2
    skill_names = {item["skill_name"] for item in body["candidate"]["skills"]}
    assert skill_names == {"Python", "React"}
    merge_skills.assert_awaited_once()


@pytest.mark.asyncio
async def test_extract_skills_from_resume_requires_uploaded_resume(
    recruiter_user: User,
    candidate_id: uuid.UUID,
) -> None:
    candidate = Candidate(
        id=candidate_id,
        full_name="Jane Doe",
        email="jane@example.com",
        resume_path=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    mock_session = AsyncMock()
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = recruiter_user
    mock_session.execute = AsyncMock(return_value=user_result)

    app = create_app()

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db
    token = create_access_token(subject=str(recruiter_user.id), role=recruiter_user.role.value)

    with patch(
        "app.api.candidates.crud_get_candidate_by_id",
        new_callable=AsyncMock,
        return_value=candidate,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(
                f"/candidates/{candidate_id}/skills/extract-from-resume",
                headers={"Authorization": f"Bearer {token}"},
            )

    app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json()["detail"] == "Candidate has no uploaded resume"
