from fastapi import FastAPI

from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(title="AI Powered Hiring System")

    @app.on_event("startup")
    async def _startup() -> None:
        # Force settings evaluation at startup (loads from .env)
        _ = settings.app_env
        _ = settings

    return app


app = create_app()
