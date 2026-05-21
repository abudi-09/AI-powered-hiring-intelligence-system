#!/usr/bin/env python3
"""Create the first admin or recruiter account."""

from __future__ import annotations

import argparse
import asyncio
import sys

from sqlalchemy import select

from app.core.security import get_password_hash
from app.db.session import AsyncSessionLocal
from app.models.user import User, UserRole


async def create_user(email: str, password: str, full_name: str, role: UserRole) -> int:
    async with AsyncSessionLocal() as db:
        existing = await db.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none() is not None:
            print(f"User already exists: {email}")
            return 1

        user = User(
            email=email,
            hashed_password=get_password_hash(password),
            full_name=full_name,
            role=role,
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    print(f"Created {role.value} user {email} ({user.id})")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap an admin or recruiter user")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--name", default="Admin User")
    parser.add_argument(
        "--role",
        default="Admin",
        choices=[role.value for role in (UserRole.Admin, UserRole.Recruiter)],
    )
    args = parser.parse_args()
    role = UserRole(args.role)
    return asyncio.run(create_user(args.email, args.password, args.name, role))


if __name__ == "__main__":
    raise SystemExit(main())
