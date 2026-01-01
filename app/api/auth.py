from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, verify_password
from app.db.session import get_db
from app.models.user import User
from app.schemas.token import Token


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token)
async def login(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Token:
    content_type = (request.headers.get("content-type") or "").lower()
    email: str | None = None
    password: str | None = None

    # Support Postman raw JSON AND OAuth2 form-encoded logins.
    try:
        if "application/json" in content_type:
            data = await request.json()
            if isinstance(data, dict):
                email = data.get("email") or data.get("username")
                password = data.get("password")
        else:
            form = await request.form()
            email = form.get("email") or form.get("username")
            password = form.get("password")
    except Exception:
        # Fall through to validation error
        email = None
        password = None

    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Missing email and/or password",
        )

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")

    access_token = create_access_token(subject=str(user.id), role=user.role.value)
    return Token(access_token=access_token, token_type="bearer")
