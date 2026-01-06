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
from app.models.skill import Skill
from app.models.user import User, UserRole
from app.schemas.candidate import CandidateCreate, CandidateRead, CandidateUpdate


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


@router.get("/", response_model=list[CandidateRead])
async def list_candidates(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(AllowedRoleDep),
) -> list[Candidate]:
    result = await db.execute(select(Candidate).order_by(Candidate.created_at.desc()))
    return list(result.scalars().all())


@router.post("/", response_model=CandidateRead, status_code=status.HTTP_201_CREATED)
async def create_candidate(
    payload: CandidateCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(AllowedRoleDep),
) -> Candidate:
    candidate = Candidate(
        full_name=payload.full_name,
        email=str(payload.email) if payload.email is not None else None,
        resume_path=payload.resume_path,
    )

    if payload.skill_ids:
        result = await db.execute(select(Skill).where(Skill.id.in_(payload.skill_ids)))
        skills = list(result.scalars().all())
        if len(skills) != len(set(payload.skill_ids)):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="One or more skills not found")
        candidate.skills = skills

    db.add(candidate)
    await db.commit()
    await db.refresh(candidate)
    return candidate


@router.get("/{candidate_id}", response_model=CandidateRead)
async def get_candidate(
    candidate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(AllowedRoleDep),
) -> Candidate:
    result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
    candidate = result.scalar_one_or_none()
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    return candidate


@router.patch("/{candidate_id}", response_model=CandidateRead)
async def update_candidate(
    candidate_id: uuid.UUID,
    payload: CandidateUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(AllowedRoleDep),
) -> Candidate:
    result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
    candidate = result.scalar_one_or_none()
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    if payload.full_name is not None:
        candidate.full_name = payload.full_name
    if payload.email is not None:
        candidate.email = str(payload.email)
    if payload.resume_path is not None:
        candidate.resume_path = payload.resume_path

    if payload.skill_ids is not None:
        if payload.skill_ids:
            skills_result = await db.execute(select(Skill).where(Skill.id.in_(payload.skill_ids)))
            skills = list(skills_result.scalars().all())
            if len(skills) != len(set(payload.skill_ids)):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="One or more skills not found")
            candidate.skills = skills
        else:
            candidate.skills = []

    await db.commit()
    await db.refresh(candidate)
    return candidate


@router.delete("/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_candidate(
    candidate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(AllowedRoleDep),
) -> None:
    result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
    candidate = result.scalar_one_or_none()
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    await db.delete(candidate)
    await db.commit()
    return None


@router.post("/{candidate_id}/resume", response_model=CandidateRead)
async def upload_candidate_resume(
    candidate_id: uuid.UUID,
    resume: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(AllowedRoleDep),
) -> Candidate:
    result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
    candidate = result.scalar_one_or_none()
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    storage_root = settings.resume_storage_path
    filename = _safe_resume_filename(resume.filename, candidate_id)
    relative_path = Path(str(candidate_id)) / filename
    full_path = storage_root / relative_path

    await _write_upload_file(resume, full_path)

    candidate.resume_path = relative_path.as_posix()
    await db.commit()
    await db.refresh(candidate)
    return candidate
