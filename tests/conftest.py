import os

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/hiring_test",
)
os.environ.setdefault("JWT_SECRET_KEY", "pytest-secret-key-not-for-production")
os.environ.setdefault("APP_ENV", "development")
