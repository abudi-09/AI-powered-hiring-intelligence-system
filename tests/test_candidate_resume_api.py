import uuid
from datetime import datetime, timezone
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.candidates import _validate_resume_extension, _validate_resume_size
from app.core.security import create_access_token, get_password_hash
from app.db.session import get_db
from app.main import create_app
from app.models.candidate import Candidate
from app.models.user import User, UserRole
from fastapi import HTTPException


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


def test_validate_resume_upload_rejects_bad_extension() -> None:
    with pytest.raises(HTTPException) as exc:
        _validate_resume_extension("resume.docx")

    assert exc.value.status_code == 400
    assert "Resume must be a .txt, .md, or .pdf file" in exc.value.detail


def test_validate_resume_upload_rejects_empty_file() -> None:
    with pytest.raises(HTTPException) as exc:
        _validate_resume_size(0)

    assert exc.value.status_code == 400
    assert exc.value.detail == "Resume file is empty"


@pytest.mark.asyncio
async def test_upload_resume_rejects_unsupported_extension(
    recruiter_user: User,
) -> None:
    candidate_id = uuid.uuid4()
    candidate = Candidate(
        id=candidate_id,
        full_name="Jane Doe",
        email="jane@example.com",
        resume_path=None,
    )

    mock_session = AsyncMock()
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = recruiter_user
    mock_db_execute = MagicMock()
    mock_db_execute.scalar_one_or_none.return_value = candidate
    mock_session.execute = AsyncMock(side_effect=[user_result, mock_db_execute])

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
                f"/candidates/{candidate_id}/resume",
                headers={"Authorization": f"Bearer {token}"},
                files={"resume": ("resume.docx", BytesIO(b"hello"), "application/octet-stream")},
            )

    app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json()["detail"] == "Resume must be a .txt, .md, or .pdf file"
