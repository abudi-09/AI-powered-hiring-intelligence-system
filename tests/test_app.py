from app.core.config import settings


def test_settings_load_with_test_environment() -> None:
    assert settings.app_env == "development"
    assert settings.database_url.startswith("postgresql+asyncpg://")
    assert settings.access_token_expire_minutes >= 1
