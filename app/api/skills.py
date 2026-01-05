from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import role_required
from app.db.session import get_db
from app.models.skill import Skill
from app.models.user import User, UserRole
from app.schemas.skill import SkillCreate, SkillRead


router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("/", response_model=list[SkillRead])
async def list_skills(db: AsyncSession = Depends(get_db)) -> list[Skill]:
    result = await db.execute(select(Skill).order_by(Skill.name.asc()))
    return list(result.scalars().all())


@router.post("/", response_model=SkillRead, status_code=status.HTTP_201_CREATED)
async def create_skill(
    payload: SkillCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(role_required(UserRole.Admin, UserRole.Recruiter, UserRole.HiringManager)),
) -> Skill:
    existing = await db.execute(select(Skill).where(Skill.name == payload.name))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Skill already exists")

    skill = Skill(name=payload.name, description=payload.description)
    db.add(skill)
    await db.commit()
    await db.refresh(skill)
    return skill
