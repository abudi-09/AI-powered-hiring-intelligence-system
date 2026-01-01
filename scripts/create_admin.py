from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import select

from app.core.security import get_password_hash
from app.db.session import AsyncSessionLocal
from app.models.user import User, UserRole


def _validate_password(password: str) -> None:
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")
    if len(password.encode("utf-8")) > 72:
        raise ValueError("Password too long (bcrypt max is 72 bytes)")
    if not any(ch.isalpha() for ch in password) or not any(ch.isdigit() for ch in password):
        raise ValueError("Password must contain at least one letter and one number")


async def _run(email: str, password: str, full_name: str) -> None:
    _validate_password(password)

    async with AsyncSessionLocal() as session:
        existing = await session.execute(select(User).where(User.email == email))
        user = existing.scalar_one_or_none()

        if user is not None:
            # Ensure existing user is admin + active
            changed = False
            if user.role != UserRole.Admin:
                user.role = UserRole.Admin
                changed = True
            if not user.is_active:
                user.is_active = True
                changed = True
            if changed:
                await session.commit()
                await session.refresh(user)
            print(f"Admin ready: {user.email} ({user.id})")
            return

        user = User(
            full_name=full_name,
            email=email,
            hashed_password=get_password_hash(password),
            role=UserRole.Admin,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

    print(f"Admin created: {user.email} ({user.id})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or promote an Admin user")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--full-name", default="Admin")
    args = parser.parse_args()

    asyncio.run(_run(args.email, args.password, args.full_name))


if __name__ == "__main__":
    main()
