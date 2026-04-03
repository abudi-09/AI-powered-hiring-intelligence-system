from app.core.config import settings
from app.main import create_app


def test_settings_load_with_test_environment() -> None:
    assert settings.app_env == "development"
    assert settings.database_url.startswith("postgresql+asyncpg://")
    assert settings.access_token_expire_minutes >= 1
    assert "http://localhost:3000" in settings.cors_origins


def test_cors_allows_configured_origin() -> None:
    app = create_app()
    cors = next(
        middleware
        for middleware in app.user_middleware
        if middleware.cls.__name__ == "CORSMiddleware"
    )
    assert "http://localhost:3000" in cors.kwargs["allow_origins"]
