import io
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, UploadFile
from httpx import ASGITransport, AsyncClient

from app.api import candidates as candidates_api
from app.core.security import create_access_token, get_password_hash
from app.db.session import get_db
from app.main import create_app
from app.models.candidate import Candidate
from app.models.user import User, UserRole
from app.schemas.candidate import CandidateRead


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


def test_safe_resume_filename_sanitizes_long_extension() -> None:
    candidate_id = uuid.uuid4()
    name = candidates_api._safe_resume_filename("resume" + "x" * 20 + ".txt", candidate_id)
    assert name.startswith(str(candidate_id))
    assert name.endswith(".txt")


def test_validate_resume_extension_and_size() -> None:
    candidates_api._validate_resume_extension("resume.pdf")
    with pytest.raises(HTTPException) as exc:
        candidates_api._validate_resume_extension("resume.exe")
    assert exc.value.status_code == 400

    candidates_api._validate_resume_size(10)
    with pytest.raises(HTTPException) as empty_exc:
        candidates_api._validate_resume_size(0)
    assert empty_exc.value.detail == "Resume file is empty"

    with pytest.raises(HTTPException) as large_exc:
        candidates_api._validate_resume_size(candidates_api._MAX_RESUME_BYTES + 1)
    assert "5 MB" in large_exc.value.detail


@pytest.mark.asyncio
async def test_write_upload_file_persists_bytes(tmp_path: Path) -> None:
    upload = UploadFile(filename="resume.txt", file=io.BytesIO(b"python fastapi"))
    destination = tmp_path / "resume.txt"
    written = await candidates_api._write_upload_file(upload, destination)
    assert written == len(b"python fastapi")
    assert destination.read_bytes() == b"python fastapi"


@pytest.mark.asyncio
async def test_write_upload_file_rejects_oversized_payload(tmp_path: Path) -> None:
    huge = b"x" * (candidates_api._MAX_RESUME_BYTES + 1)
    upload = UploadFile(filename="big.txt", file=io.BytesIO(huge))
    destination = tmp_path / "big.txt"
    with pytest.raises(HTTPException) as exc:
        await candidates_api._write_upload_file(upload, destination)
    assert exc.value.status_code == 400
    assert not destination.exists()


@pytest.mark.asyncio
async def test_candidate_to_read_maps_skill_rows() -> None:
    candidate_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    candidate = Candidate(
        id=candidate_id,
        full_name="Jane",
        email="jane@example.com",
        resume_path=None,
        created_at=now,
        updated_at=now,
    )
    skill_id = uuid.uuid4()
    mock_db = AsyncMock()
    skills_result = MagicMock()
    skills_result.all.return_value = [(skill_id, "Python", "senior", 5.0)]
    mock_db.execute = AsyncMock(return_value=skills_result)

    read = await candidates_api._candidate_to_read(mock_db, candidate)
    assert read.skills[0].skill_name == "Python"


@pytest.mark.asyncio
async def test_upload_and_extract_resume_routes(recruiter_user: User, tmp_path: Path) -> None:
    candidate_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    candidate = Candidate(
        id=candidate_id,
        full_name="Jane",
        email="jane@example.com",
        resume_path=None,
        created_at=now,
        updated_at=now,
    )
    candidate_read = CandidateRead(
        id=candidate_id,
        full_name="Jane",
        email="jane@example.com",
        resume_path=f"{candidate_id}/resume.txt",
        skills=[],
        created_at=now,
        updated_at=now,
    )

    def _auth_result():
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = recruiter_user
        return user_result

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(side_effect=lambda *_a, **_k: _auth_result())
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
        "app.api.candidates.crud_set_candidate_resume_path",
        new_callable=AsyncMock,
        return_value=candidate,
    ), patch(
        "app.api.candidates._candidate_to_read",
        new_callable=AsyncMock,
        return_value=candidate_read,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            upload_response = await client.post(
                f"/candidates/{candidate_id}/resume",
                headers={"Authorization": f"Bearer {token}"},
                files={"resume": ("resume.txt", b"python developer", "text/plain")},
            )

    app.dependency_overrides.clear()
    assert upload_response.status_code == 200

    skill_id = uuid.uuid4()
    skills_lookup = MagicMock()
    skills_lookup.all.return_value = [(skill_id, "Python")]
    candidate.resume_path = f"{candidate_id}/resume.txt"
    resume_file = tmp_path / str(candidate_id) / "resume.txt"
    resume_file.parent.mkdir(parents=True, exist_ok=True)
    resume_file.write_text("python developer", encoding="utf-8")

    mock_session.execute = AsyncMock(side_effect=[_auth_result(), skills_lookup])
    app.dependency_overrides[get_db] = override_get_db

    with patch.object(candidates_api.settings, "resume_storage_path", tmp_path), patch(
        "app.api.candidates.crud_get_candidate_by_id",
        new_callable=AsyncMock,
        return_value=candidate,
    ), patch(
        "app.api.candidates.crud_merge_candidate_skills",
        new_callable=AsyncMock,
    ), patch(
        "app.api.candidates._candidate_to_read",
        new_callable=AsyncMock,
        return_value=candidate_read,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            extract_response = await client.post(
                f"/candidates/{candidate_id}/skills/extract-from-resume",
                headers={"Authorization": f"Bearer {token}"},
            )

    app.dependency_overrides.clear()
    assert extract_response.status_code == 200


@pytest.mark.asyncio
async def test_extract_resume_errors(recruiter_user: User, tmp_path: Path) -> None:
    candidate_id = uuid.uuid4()
    candidate = Candidate(
        id=candidate_id,
        full_name="Jane",
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
            no_resume = await client.post(
                f"/candidates/{candidate_id}/skills/extract-from-resume",
                headers={"Authorization": f"Bearer {token}"},
            )

    candidate.resume_path = "missing/resume.txt"
    with patch.object(candidates_api.settings, "resume_storage_path", tmp_path), patch(
        "app.api.candidates.crud_get_candidate_by_id",
        new_callable=AsyncMock,
        return_value=candidate,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            missing_file = await client.post(
                f"/candidates/{candidate_id}/skills/extract-from-resume",
                headers={"Authorization": f"Bearer {token}"},
            )

    app.dependency_overrides.clear()

    assert no_resume.status_code == 400
    assert missing_file.status_code == 404
