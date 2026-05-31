import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.crud.skill import create_skill, delete_skill, get_skill_by_id, list_skills, update_skill
from app.models.skill import Skill
from app.schemas.skill import SkillCreate, SkillUpdate


@pytest.mark.asyncio
async def test_get_skill_by_id_returns_404_for_missing_skill() -> None:
    mock_db = AsyncMock()
    lookup = MagicMock()
    lookup.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=lookup)

    with pytest.raises(HTTPException) as exc:
        await get_skill_by_id(mock_db, uuid.uuid4())

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_list_skills_returns_sorted_rows() -> None:
    mock_db = AsyncMock()
    skill = Skill(
        id=uuid.uuid4(),
        name="Python",
        category="Language",
        created_at=datetime.now(timezone.utc),
    )
    result = MagicMock()
    result.scalars.return_value.all.return_value = [skill]
    mock_db.execute = AsyncMock(return_value=result)

    skills = await list_skills(mock_db)

    assert len(skills) == 1
    assert skills[0].name == "Python"


@pytest.mark.asyncio
async def test_create_skill_rejects_duplicate_name() -> None:
    mock_db = AsyncMock()
    existing = MagicMock()
    existing.scalar_one_or_none.return_value = object()
    mock_db.execute = AsyncMock(return_value=existing)

    with pytest.raises(HTTPException) as exc:
        await create_skill(mock_db, SkillCreate(name="Python", category="Language"))

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_create_skill_persists_new_row() -> None:
    mock_db = AsyncMock()
    missing = MagicMock()
    missing.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=missing)
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    skill = await create_skill(mock_db, SkillCreate(name="  Rust  ", category="Language"))

    assert skill.name == "Rust"
    mock_db.add.assert_called_once()
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_and_delete_skill() -> None:
    skill_id = uuid.uuid4()
    skill = Skill(
        id=skill_id,
        name="Go",
        category="Language",
        created_at=datetime.now(timezone.utc),
    )
    mock_db = AsyncMock()
    lookup = MagicMock()
    lookup.scalar_one_or_none.return_value = skill
    duplicate = MagicMock()
    duplicate.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(side_effect=[lookup, duplicate])
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    mock_db.delete = AsyncMock()

    updated = await update_skill(
        mock_db,
        skill_id,
        SkillUpdate(name="Golang", category="Backend"),
    )
    assert updated.name == "Golang"

    mock_db.execute = AsyncMock(return_value=lookup)
    await delete_skill(mock_db, skill_id)
    mock_db.delete.assert_awaited_once_with(skill)
