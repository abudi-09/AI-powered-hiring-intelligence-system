from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Liveness probe for load balancers and container orchestration."""
    return {
        "status": "ok",
        "app_env": settings.app_env,
    }


@router.get("/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    """Readiness probe verifying configuration and database connectivity."""
    _ = settings.database_url
    _ = settings.jwt_secret_key

    try:
        await db.execute(text("SELECT 1"))
        database_status = "connected"
    except Exception:
        database_status = "unavailable"

    return {
        "status": "ready" if database_status == "connected" else "degraded",
        "app_env": settings.app_env,
        "database": database_status,
    }
