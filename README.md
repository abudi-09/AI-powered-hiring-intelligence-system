# AI-Powered Hiring Intelligence Systems

Personal backend for recruiter-facing hiring analytics: weighted candidate–job matching, resume skill extraction, dashboard intelligence metrics, and a rule-based chat assistant for hiring queries.

Built with FastAPI, async PostgreSQL, Alembic, and JWT role-based access.

## What this project does

- **Match scoring** — weighted skill overlap with experience bonuses and missing-skill penalties (`app/services/scoring.py`)
- **Batch job scoring** — score all candidates against a job in one request (`POST /jobs/{job_id}/matches/auto-score`)
- **Resume skill extraction** — parses plain-text resumes with aliases, dedicated skills sections, and level detection
- **Hiring intelligence** — job difficulty, candidate competitiveness, skill demand/supply, match distribution, and recruiter KPIs
- **Recruiter chat** — intent detection routes queries to analytics, recommendations, insights, and match explanations
- **Role-based API** — Admin, Recruiter, Hiring Manager, and Candidate roles with JWT auth

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux
pip install -r requirements.txt -r requirements-dev.txt
copy .env.example .env          # then edit DATABASE_URL and JWT_SECRET_KEY
alembic upgrade head
uvicorn app.main:app --reload
```

Interactive API docs: `http://127.0.0.1:8000/docs`

## Tests

```bash
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest tests/ -v
python -m pytest tests/ --cov=app --cov-report=term-missing
```

Current suite: **108+ tests**, **~78% coverage** across services, CRUD validation, API routes, and chat pipeline flows.

Run the pre-upload verifier:

```bash
python scripts/verify_submission.py
```

## Docker

Build and run the API container:

```bash
docker build -t hiring-intelligence .
docker run --rm -p 8000:8000 \
  -e DATABASE_URL=postgresql+asyncpg://postgres:postgres@host.docker.internal:5432/hiring \
  -e JWT_SECRET_KEY=replace-with-a-long-random-secret \
  hiring-intelligence
```

Run PostgreSQL and the app together:

```bash
docker compose up --build
```

Then apply migrations from your host (or an exec shell):

```bash
alembic upgrade head
```

Health checks:

- Liveness: `GET /health`
- Readiness: `GET /ready` (includes database connectivity)

## Project layout

| Path | Purpose |
|---|---|
| `app/services/scoring.py` | Pure match-score calculations |
| `app/services/intelligence_metrics.py` | Pure hiring analytics formulas |
| `app/services/skill_extractor.py` | Resume text → structured skills |
| `app/services/intent_detector.py` | Recruiter query intent routing |
| `app/services/conversation_orchestrator.py` | Chat pipeline orchestration |
| `app/services/intelligence_engine.py` | DB-backed intelligence orchestration |
| `app/crud/` | Persistence and validation layer |
| `tests/` | Unit, integration, and API pipeline tests |
| `scripts/verify_submission.py` | Pre-upload sanity checks |

## Notable endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/auth/login` | JWT authentication |
| `GET` | `/health` | Liveness probe |
| `GET` | `/ready` | Readiness probe with DB check |
| `POST` | `/candidates/{id}/resume` | Upload resume file |
| `POST` | `/candidates/{id}/skills/extract-from-resume` | Extract skills from uploaded resume text |
| `POST` | `/matches/auto-score` | Score one candidate–job pair |
| `POST` | `/jobs/{job_id}/matches/auto-score` | Batch score candidates for a job |
| `GET` | `/intelligence/job/{job_id}` | Job hiring difficulty and scarcity metrics |
| `POST` | `/intelligence/generate/recruiter/{recruiter_id}` | Generate recruiter KPI snapshot |
| `POST` | `/chat/query` | Recruiter assistant with intent routing |

See `/docs` for the full API surface.

## Environment variables

| Variable | Description |
|---|---|
| `DATABASE_URL` | Async PostgreSQL URL (`postgresql+asyncpg://...`) |
| `JWT_SECRET_KEY` | Secret for signing access tokens |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token lifetime (default 60) |
| `RESUME_STORAGE_PATH` | Directory for uploaded resumes |
| `APP_ENV` | `development` or `production` |

## Silver / AfterQuery upload checklist

Before zipping the repo:

1. Run `python -m pytest` and `python scripts/verify_submission.py`
2. Confirm `.env` is **not** tracked and not included in the zip
3. Include the full `.git/` directory for history review
4. Exclude local artifacts: `.venv/`, `storage/`, `__pycache__/`, `.coverage`
5. Upload as **Python**; attach `Dockerfile` separately if required by the form

Recommended zip contents: source, tests, Alembic migrations, `Dockerfile`, `docker-compose.yml`, `.env.example`, and `.git/`.
