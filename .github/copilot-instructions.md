# Copilot instructions (backend)

## Repo orientation

- **Repo root is `backend/`** (it contains `.git/`). Most commands should be run from this folder.
- FastAPI app entrypoint: `app/main.py` (`create_app()` registers all routers).
- Layering pattern:
  - `app/api/`: HTTP routes (FastAPI `APIRouter`), dependency injection, auth/RBAC
  - `app/crud/`: DB reads/writes (async SQLAlchemy), commits + refresh
  - `app/services/`: “engine” modules for deterministic analytics (e.g. `IntelligenceEngine`)
  - `app/models/`: SQLAlchemy ORM models (UUID PKs, Postgres JSONB, relationships)
  - `app/schemas/`: Pydantic v2 DTOs (`ConfigDict(from_attributes=True)` for ORM -> schema)

## Key workflows (Windows-friendly)

- Install deps: `pip install -r requirements.txt`
- Run API (from `backend/`): `uvicorn app.main:app --reload`
- Migrations (uses `DATABASE_URL` from `backend/.env`): `alembic upgrade head`
- Smoke test script (DB required): `python test_job_skills.py`
- Create/promote admin: `python scripts/create_admin.py --email admin@example.com --password Admin1234 --full-name "Admin"`

## Project conventions to follow

- **Async SQLAlchemy everywhere**: route handlers accept `AsyncSession` via DI (`db: Annotated[AsyncSession, Depends(get_db)]`).
- **RBAC**: endpoints commonly enforce roles via `role_required(...)` and ignore the returned user: `_: User = Depends(AllowedRoleDep)` (see `app/api/intelligence.py`).
- **CRUD shape**:
  - Read: `await db.execute(select(Model).where(...))` then `scalar_one_or_none()`
  - Write: mutate ORM objects, then `await db.commit()` and `await db.refresh(obj)`
  - Replace association lists by clearing relationship then appending (e.g. `job.skills.clear()` in `app/crud/job.py`).
- **Analytics engines are deterministic**: `app/services/intelligence_engine.py` computes metrics using only DB state; keep this style when adding/adjusting metrics.

## Alembic / model gotchas

- Alembic is configured for async in `alembic/env.py` and reads the DB URL from `app/core/config.py` (which loads `backend/.env`). The `alembic.ini` URL is not the source of truth.
- Model discovery for migrations relies on `app/db/base.py` importing `app.models` to populate `Base.metadata`.

## Where to implement changes

- New endpoint: add schema in `app/schemas/` → CRUD in `app/crud/` (or service in `app/services/`) → wire route in `app/api/` → include router in `app/main.py` only if it’s a new router module.
