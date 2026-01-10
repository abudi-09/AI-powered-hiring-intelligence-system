from fastapi import FastAPI

from app.api.analytics import router as analytics_router
from app.api.auth import router as auth_router
from app.api.candidates import router as candidates_router
from app.api.insights import router as insights_router
from app.api.jobs import router as jobs_router
from app.api.matches import router as matches_router
from app.api.narratives import router as narratives_router
from app.api.recommendations import router as recommendations_router
from app.api.skills import router as skills_router
from app.api.users import router as users_router
from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(title="AI Powered Hiring System")

    app.include_router(auth_router)
    app.include_router(skills_router)
    app.include_router(candidates_router)
    app.include_router(jobs_router)
    app.include_router(matches_router)
    app.include_router(analytics_router)
    app.include_router(insights_router)
    app.include_router(recommendations_router)
    app.include_router(narratives_router)
    app.include_router(users_router)

    @app.on_event("startup")
    async def _startup() -> None:
        # Force settings evaluation at startup (loads from .env)
        _ = settings.app_env
        _ = settings

    return app


app = create_app()
