#!/usr/bin/env python3
"""Wait until PostgreSQL accepts connections."""

from __future__ import annotations

import asyncio
import os
import sys

import asyncpg


def _asyncpg_dsn(database_url: str) -> str:
    if database_url.startswith("postgresql+asyncpg://"):
        return database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    return database_url


async def wait_for_database(timeout_seconds: int = 60) -> None:
    dsn = _asyncpg_dsn(os.environ["DATABASE_URL"])
    for attempt in range(timeout_seconds):
        try:
            conn = await asyncpg.connect(dsn)
            await conn.close()
            return
        except Exception:
            await asyncio.sleep(1)
    raise RuntimeError(f"Database unavailable after {timeout_seconds}s")


def main() -> int:
    try:
        asyncio.run(wait_for_database())
    except Exception as exc:
        print(exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
