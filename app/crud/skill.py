from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.skill import Skill
from app.schemas.skill import SkillCreate, SkillUpdate


def _normalize_skill_name(name: str) -> str:
    return name.strip()


async def get_skill_by_id(db: AsyncSession, skill_id: uuid.UUID) -> Skill:
    result = await db.execute(select(Skill).where(Skill.id == skill_id))
    skill = result.scalar_one_or_none()
    if skill is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")
    return skill


async def list_skills(db: AsyncSession) -> list[Skill]:
    result = await db.execute(select(Skill).order_by(Skill.name.asc()))
    return list(result.scalars().all())


async def create_skill(db: AsyncSession, payload: SkillCreate) -> Skill:
    normalized_name = _normalize_skill_name(payload.name)

    existing = await db.execute(
        select(Skill).where(func.lower(Skill.name) == func.lower(normalized_name))
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Skill already exists")

    skill = Skill(name=normalized_name, category=payload.category)
    db.add(skill)
    await db.commit()
    await db.refresh(skill)
    return skill


async def update_skill(db: AsyncSession, skill_id: uuid.UUID, payload: SkillUpdate) -> Skill:
    skill = await get_skill_by_id(db, skill_id)

    if payload.name is not None:
        normalized_name = _normalize_skill_name(payload.name)

        existing = await db.execute(
            select(Skill).where(
                func.lower(Skill.name) == func.lower(normalized_name),
                Skill.id != skill_id,
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Skill already exists")

        skill.name = normalized_name

    if payload.category is not None:
        skill.category = payload.category

    await db.commit()
    await db.refresh(skill)
    return skill


async def delete_skill(db: AsyncSession, skill_id: uuid.UUID) -> None:
    skill = await get_skill_by_id(db, skill_id)
    await db.delete(skill)
    await db.commit()
