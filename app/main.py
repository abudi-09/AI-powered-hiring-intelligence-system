from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.analytics import router as analytics_router
from app.api.auth import router as auth_router
from app.api.candidates import router as candidates_router
from app.api.chat import router as chat_router
from app.api.health import router as health_router
from app.api.insights import router as insights_router
from app.api.intelligence import router as intelligence_router
from app.api.jobs import router as jobs_router
from app.api.matches import router as matches_router
from app.api.narratives import router as narratives_router
from app.api.recommendations import router as recommendations_router
from app.api.skills import router as skills_router
from app.api.users import router as users_router
from app.core.config import settings
from app.core.middleware import RequestLoggingMiddleware


def configure_logging() -> None:
    level = logging.DEBUG if settings.app_env == "development" else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    _ = settings.app_env
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Meridian Platform API", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestLoggingMiddleware)

    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(skills_router)
    app.include_router(candidates_router)
    app.include_router(jobs_router)
    app.include_router(matches_router)
    app.include_router(analytics_router)
    app.include_router(insights_router)
    app.include_router(recommendations_router)
    app.include_router(narratives_router)
    app.include_router(intelligence_router)
    app.include_router(chat_router)
    app.include_router(users_router)

    return app


app = create_app()
