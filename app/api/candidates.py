from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import Final

import anyio
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import role_required
from app.core.config import settings
from app.db.session import get_db
from app.models.candidate import Candidate
from app.models.candidate_skill import CandidateSkill
from app.models.skill import Skill
from app.models.user import User, UserRole
from app.crud.candidate import (
    create_candidate as crud_create_candidate,
    delete_candidate as crud_delete_candidate,
    get_candidate_by_id as crud_get_candidate_by_id,
    list_candidates as crud_list_candidates,
    merge_candidate_skills as crud_merge_candidate_skills,
    update_candidate as crud_update_candidate,
)
from app.schemas.candidate import (
    CandidateCreate,
    CandidateRead,
    CandidateUpdate,
    CandidateSkillRead,
    ResumeSkillExtractionRead,
)
from app.services.skill_extractor import SkillExtractor


router = APIRouter(prefix="/candidates", tags=["candidates"])


AllowedRoleDep = role_required(UserRole.Admin, UserRole.Recruiter, UserRole.HiringManager)


_FILENAME_SAFE_RE: Final[re.Pattern[str]] = re.compile(r"[^A-Za-z0-9._-]+")


def _safe_resume_filename(original_filename: str | None, candidate_id: uuid.UUID) -> str:
    ext = ""
    if original_filename:
        ext = Path(original_filename).suffix
        if len(ext) > 10:
            ext = ""
        ext = _FILENAME_SAFE_RE.sub("", ext)

    return f"{candidate_id}_{uuid.uuid4().hex}{ext}"


async def _write_upload_file(upload: UploadFile, destination: Path) -> None:
    def _write_sync() -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("wb") as f:
            while True:
                chunk = upload.file.read(1024 * 1024)
                if not chunk:
                    break
                f.write(chunk)

    await anyio.to_thread.run_sync(_write_sync)


async def _candidate_to_read(db: AsyncSession, candidate: Candidate) -> CandidateRead:
    result = await db.execute(
        select(CandidateSkill.skill_id, Skill.name, CandidateSkill.level, CandidateSkill.years_experience)
        .join(Skill, Skill.id == CandidateSkill.skill_id)
        .where(CandidateSkill.candidate_id == candidate.id)
        .order_by(Skill.name.asc())
    )

    skills_out: list[CandidateSkillRead] = []
    for skill_id, skill_name, level, years_experience in result.all():
        skills_out.append(
            CandidateSkillRead(
                skill_id=skill_id,
                skill_name=skill_name,
                level=level,
                years_experience=years_experience,
            )
        )

    return CandidateRead(
        id=candidate.id,
        full_name=candidate.full_name,
        email=candidate.email,
        resume_path=candidate.resume_path,
        skills=skills_out,
        created_at=candidate.created_at,
        updated_at=candidate.updated_at,
    )


@router.get("/", response_model=list[CandidateRead])
async def list_candidates(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(AllowedRoleDep),
) -> list[CandidateRead]:
    candidates = await crud_list_candidates(db)
    return [await _candidate_to_read(db, c) for c in candidates]


@router.post("/", response_model=CandidateRead, status_code=status.HTTP_201_CREATED)
async def create_candidate(
    payload: CandidateCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(AllowedRoleDep),
) -> CandidateRead:
    candidate = await crud_create_candidate(db, payload)
    return await _candidate_to_read(db, candidate)


@router.get("/{candidate_id}", response_model=CandidateRead)
async def get_candidate(
    candidate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(AllowedRoleDep),
) -> CandidateRead:
    candidate = await crud_get_candidate_by_id(db, candidate_id)
    return await _candidate_to_read(db, candidate)


@router.patch("/{candidate_id}", response_model=CandidateRead)
async def update_candidate(
    candidate_id: uuid.UUID,
    payload: CandidateUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(AllowedRoleDep),
) -> CandidateRead:
    candidate = await crud_update_candidate(db, candidate_id, payload)
    return await _candidate_to_read(db, candidate)


@router.delete("/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_candidate(
    candidate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(AllowedRoleDep),
) -> None:
    await crud_delete_candidate(db, candidate_id)
    return None


@router.post("/{candidate_id}/resume", response_model=CandidateRead)
async def upload_candidate_resume(
    candidate_id: uuid.UUID,
    resume: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(AllowedRoleDep),
) -> CandidateRead:
    candidate = await crud_get_candidate_by_id(db, candidate_id)

    storage_root = settings.resume_storage_path
    filename = _safe_resume_filename(resume.filename, candidate_id)
    relative_path = Path(str(candidate_id)) / filename
    full_path = storage_root / relative_path

    await _write_upload_file(resume, full_path)

    candidate.resume_path = relative_path.as_posix()
    await db.commit()
    await db.refresh(candidate)
    return await _candidate_to_read(db, candidate)


@router.post("/{candidate_id}/skills/extract-from-resume", response_model=ResumeSkillExtractionRead)
async def extract_skills_from_resume(
    candidate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(AllowedRoleDep),
) -> ResumeSkillExtractionRead:
    candidate = await crud_get_candidate_by_id(db, candidate_id)
    if not candidate.resume_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Candidate has no uploaded resume",
        )

    resume_path = settings.resume_storage_path / candidate.resume_path
    if not resume_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume file not found on disk",
        )

    try:
        resume_text = resume_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resume must be UTF-8 plain text for skill extraction",
        ) from exc

    skills_result = await db.execute(select(Skill.id, Skill.name).order_by(Skill.name))
    skill_rows = skills_result.all()
    skill_name_to_id = {name: skill_id for skill_id, name in skill_rows}

    extractor = SkillExtractor()
    extracted = extractor.extract_from_text(
        resume_text,
        [name for _, name in skill_rows],
    )
    if not extracted:
        return ResumeSkillExtractionRead(
            extracted_count=0,
            candidate=await _candidate_to_read(db, candidate),
        )

    merge_payload = [
        {
            "skill_id": skill_name_to_id[item.skill_name],
            "level": item.level,
            "years_experience": item.years_experience,
        }
        for item in extracted
        if item.skill_name in skill_name_to_id
    ]
    await crud_merge_candidate_skills(db, candidate, merge_payload)
    await db.commit()
    await db.refresh(candidate)

    return ResumeSkillExtractionRead(
        extracted_count=len(merge_payload),
        candidate=await _candidate_to_read(db, candidate),
    )
