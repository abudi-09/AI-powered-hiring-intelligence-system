from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import role_required
from app.crud.skill import create_skill as crud_create_skill, delete_skill, get_skill_by_id, list_skills, update_skill
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.skill import SkillCreate, SkillRead, SkillUpdate


router = APIRouter(prefix="/skills", tags=["skills"])

ReadRoleDep = role_required(UserRole.Admin, UserRole.Recruiter, UserRole.HiringManager)


@router.get("/", response_model=list[SkillRead])
async def skills_list(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(ReadRoleDep),
):
    return await list_skills(db)


@router.get("/{skill_id}", response_model=SkillRead)
async def skills_get(
    skill_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(ReadRoleDep),
):
    return await get_skill_by_id(db, skill_id)


@router.post("/", response_model=SkillRead, status_code=status.HTTP_201_CREATED)
async def skills_create(
    payload: SkillCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(role_required(UserRole.Admin)),
):
    return await crud_create_skill(db, payload)


@router.put("/{skill_id}", response_model=SkillRead)
async def skills_update(
    skill_id: uuid.UUID,
    payload: SkillUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(role_required(UserRole.Admin)),
):
    return await update_skill(db, skill_id, payload)


@router.delete("/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
async def skills_delete(
    skill_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(role_required(UserRole.Admin)),
):
    await delete_skill(db, skill_id)
    return None
