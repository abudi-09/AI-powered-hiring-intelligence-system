from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, role_required
from app.crud.user import (
    create_user as crud_create_user,
    deactivate_user as crud_deactivate_user,
    get_user_by_id as crud_get_user_by_id,
    list_users as crud_list_users,
    update_user as crud_update_user,
)
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
async def read_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.get("/", response_model=list[UserRead])
async def list_users(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(role_required(UserRole.Admin)),
) -> list[User]:
    return await crud_list_users(db)


@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(role_required(UserRole.Admin)),
) -> User:
    return await crud_create_user(db, payload)


@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(role_required(UserRole.Admin)),
) -> User:
    return await crud_get_user_by_id(db, user_id)


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: uuid.UUID,
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(role_required(UserRole.Admin)),
) -> User:
    return await crud_update_user(db, user_id, payload)


@router.post("/{user_id}/deactivate", response_model=UserRead)
async def deactivate_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(role_required(UserRole.Admin)),
) -> User:
    return await crud_deactivate_user(db, user_id)
