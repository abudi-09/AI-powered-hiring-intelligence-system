from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.users import router as users_router
from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(title="AI Powered Hiring System")

    app.include_router(auth_router)
    app.include_router(users_router)

    @app.on_event("startup")
    async def _startup() -> None:
        # Force settings evaluation at startup (loads from .env)
        _ = settings.app_env
        _ = settings

    return app


app = create_app()
