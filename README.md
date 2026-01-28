# AI-Powered Hiring Intelligence Systems

Personal backend for recruiter-facing hiring analytics: weighted candidate–job matching, resume skill extraction, dashboard intelligence metrics, and a rule-based chat assistant for hiring queries.

Built with FastAPI, async PostgreSQL, Alembic, and JWT role-based access.

## What this project does

- **Match scoring** — weighted skill overlap with experience bonuses and missing-skill penalties (`app/services/scoring.py`)
- **Resume skill extraction** — parses plain-text resumes against the skill catalog and merges results onto candidate profiles
- **Hiring intelligence** — deterministic metrics for job difficulty, candidate competitiveness, skill demand/supply, and recruiter performance
- **Recruiter chat** — intent detection routes queries to analytics, recommendations, and match explanations
- **Role-based API** — Admin, Recruiter, Hiring Manager, and Candidate roles with JWT auth

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env          # then edit DATABASE_URL and JWT_SECRET_KEY
alembic upgrade head
uvicorn app.main:app --reload
```

Interactive API docs: `http://127.0.0.1:8000/docs`

## Tests

```bash
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest tests/ -v
```

The test suite focuses on domain logic (scoring, intelligence metrics, resume extraction, intent detection) rather than boilerplate CRUD wiring.

## Docker

```bash
docker build -t hiring-intelligence .
docker run --rm -p 8000:8000 hiring-intelligence
```

Provide `DATABASE_URL` and `JWT_SECRET_KEY` at runtime when connecting to a real database.

## Project layout

| Path | Purpose |
|---|---|
| `app/services/scoring.py` | Pure match-score calculations |
| `app/services/intelligence_metrics.py` | Pure hiring analytics formulas |
| `app/services/skill_extractor.py` | Resume text → structured skills |
| `app/services/intent_detector.py` | Recruiter query intent routing |
| `app/services/intelligence_engine.py` | DB-backed intelligence orchestration |
| `tests/` | Behavioral unit tests for core logic |

## Notable endpoints

- `POST /auth/login` — JWT authentication
- `POST /candidates/{id}/resume` — upload resume file
- `POST /candidates/{id}/skills/extract-from-resume` — extract skills from uploaded UTF-8 resume text
- `POST /matches/` — upsert candidate–job match scores
- `GET /intelligence/jobs/{job_id}` — job hiring difficulty and scarcity metrics
- `POST /chat/query` — recruiter assistant with intent routing

See `/docs` for the full API surface.

## Environment variables

| Variable | Description |
|---|---|
| `DATABASE_URL` | Async PostgreSQL URL (`postgresql+asyncpg://...`) |
| `JWT_SECRET_KEY` | Secret for signing access tokens |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token lifetime (default 60) |
| `RESUME_STORAGE_PATH` | Directory for uploaded resumes |
| `APP_ENV` | `development` or `production` |
