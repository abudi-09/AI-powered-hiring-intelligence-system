from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi import Form
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, verify_password
from app.db.session import get_db
from app.models.user import User
from app.schemas.token import Token


router = APIRouter(prefix="/auth", tags=["auth"])


class LoginForm:
    def __init__(
        self,
        password: Annotated[str, Form()],
        email: Annotated[str | None, Form()] = None,
        username: Annotated[str | None, Form()] = None,
    ) -> None:
        # Accept either 'email' or OAuth2's standard 'username'.
        self.email = email or username
        self.password = password


@router.post("/login", response_model=Token)
async def login(
    form_data: LoginForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> Token:
    if not form_data.email:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Missing email",
        )

    result = await db.execute(select(User).where(User.email == form_data.email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")

    access_token = create_access_token(subject=str(user.id), role=user.role.value)
    return Token(access_token=access_token, token_type="bearer")
