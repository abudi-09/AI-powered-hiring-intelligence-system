# AI-Powered-Hiring-Intelligence-System

AI-powered system that automates **candidate-job matching**, **skill extraction**, and **role-based management**. Built with **FastAPI**, **PostgreSQL**, and **async SQLAlchemy**. AI analyzes resumes and job descriptions to generate **match scores** and provide **recommendations** for recruiters and hiring managers.

## **Key Features**

- **Candidate Management:** Profiles, resumes, and extracted skills
- **Job Management:** Create and manage job postings with required skills
- **AI Matching:** Candidate-job match scores with explanations
- **Role-Based Access:** Admin, Recruiter, Hiring Manager with different permissions
- **Database:** Async PostgreSQL with migrations via Alembic
- **API Ready:** Modular FastAPI backend

---

## **Setup Instructions**

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/AI-Powered-Hiring-Intelligence-System.git
cd AI-Powered-Hiring-Intelligence-System
```

### 2. Create virtual environment

```bash
python -m venv .venv
# Activate
source .venv/bin/activate   # Linux/macOS
.venv\Scripts\activate      # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root:

```
DATABASE_URL=postgresql+asyncpg://user:password@localhost/db_name
JWT_SECRET_KEY=your_secret_key
ACCESS_TOKEN_EXPIRE_MINUTES=60
RESUME_STORAGE_PATH=/path/to/resumes
APP_ENV=development
```

### 5. Run the application

```bash
uvicorn app.main:app --reload
```

### 6. Run database migrations

```bash
alembic upgrade head
```

## **Technologies Used**

- **Backend:** FastAPI, Python 3.10+
- **Database:** PostgreSQL, async SQLAlchemy, Alembic
- **Authentication:** JWT (JSON Web Tokens)
- **AI/ML:** Resume parsing and skill extraction modules (planned)
- **Deployment:** Vercel or cloud backend

---

## **API Endpoints (Documentation)**

Base URL (local): `http://127.0.0.1:8000`

### Authentication

Most endpoints are protected and require this header:

`Authorization: Bearer <access_token>`

How to get the token:

#### `POST /auth/login` (Public)

- **What it does:** Authenticates a user and returns a JWT.
- **Request (x-www-form-urlencoded / form-data):**
  - `username` (email)
  - `password`
- **Also supported (Postman-friendly JSON):**
  - `{ "email": "user@example.com", "password": "Password123" }`
- **Response:**
  - `{ "access_token": "...", "token_type": "bearer" }`

### Users (Admin-only management)

#### `GET /users/me` (Authenticated)

- **What it does:** Returns the currently authenticated user.
- **Auth:** Any logged-in user.
- **Response:** `UserRead` (id, full_name, email, role, is_active, timestamps)

#### `GET /users/` (Admin)

- **What it does:** Lists all users.
- **Auth:** `Admin` only.
- **Response:** `list[UserRead]`

#### `POST /users/` (Admin)

- **What it does:** Creates a new user.
- **Auth:** `Admin` only.
- **Request (JSON):** `UserCreate`
  - `full_name` (string)
  - `email` (email)
  - `password` (8–72 chars, must include letters + numbers)
  - `role` (`Admin` | `Recruiter` | `HiringManager` | `Candidate`) (optional; defaults to `Recruiter`)
- **Response:** `UserRead`

#### `GET /users/{user_id}` (Admin)

- **What it does:** Fetches a user by UUID.
- **Auth:** `Admin` only.
- **Path params:** `user_id` (UUID)
- **Response:** `UserRead`

#### `PATCH /users/{user_id}` (Admin)

- **What it does:** Updates user fields.
- **Auth:** `Admin` only.
- **Path params:** `user_id` (UUID)
- **Request (JSON):** `UserUpdate` (any subset)
  - `full_name`, `password`, `role`, `is_active`
- **Response:** `UserRead`

#### `POST /users/{user_id}/deactivate` (Admin)

- **What it does:** Sets `is_active=false` for the user.
- **Auth:** `Admin` only.
- **Path params:** `user_id` (UUID)
- **Response:** `UserRead`

### Skills

#### `GET /skills/` (Public)

- **What it does:** Lists all skills.
- **Auth:** None.
- **Response:** `list[SkillRead]`

#### `POST /skills/` (Admin / Recruiter / HiringManager)

- **What it does:** Creates a new skill.
- **Auth:** `Admin`, `Recruiter`, `HiringManager`.
- **Request (JSON):** `SkillCreate`
  - `name`, `description` (optional)
- **Response:** `SkillRead`

### Candidates (Admin / Recruiter / HiringManager)

#### `GET /candidates/`

- **What it does:** Lists candidates (newest first).
- **Auth:** `Admin`, `Recruiter`, `HiringManager`.
- **Response:** `list[CandidateRead]`

#### `POST /candidates/`

- **What it does:** Creates a candidate profile and optionally attaches skills.
- **Auth:** `Admin`, `Recruiter`, `HiringManager`.
- **Request (JSON):** `CandidateCreate`
  - `full_name`
  - `email` (optional)
  - `resume_path` (optional string; normally set via resume upload endpoint)
  - `skill_ids` (optional list of UUIDs)
- **Response:** `CandidateRead`

#### `GET /candidates/{candidate_id}`

- **What it does:** Gets a candidate by UUID.
- **Auth:** `Admin`, `Recruiter`, `HiringManager`.
- **Path params:** `candidate_id` (UUID)
- **Response:** `CandidateRead`

#### `PATCH /candidates/{candidate_id}`

- **What it does:** Updates candidate fields and/or replaces skill list.
- **Auth:** `Admin`, `Recruiter`, `HiringManager`.
- **Path params:** `candidate_id` (UUID)
- **Request (JSON):** `CandidateUpdate` (any subset)
  - `full_name`, `email`, `resume_path`, `skill_ids`
- **Response:** `CandidateRead`

#### `DELETE /candidates/{candidate_id}`

- **What it does:** Deletes a candidate.
- **Auth:** `Admin`, `Recruiter`, `HiringManager`.
- **Path params:** `candidate_id` (UUID)
- **Response:** `204 No Content`

#### `POST /candidates/{candidate_id}/resume`

- **What it does:** Uploads a resume file and stores it under `RESUME_STORAGE_PATH`, then updates `Candidate.resume_path`.
- **Auth:** `Admin`, `Recruiter`, `HiringManager`.
- **Path params:** `candidate_id` (UUID)
- **Request (multipart/form-data):**
  - field name: `resume` (file)
- **Response:** `CandidateRead` (with `resume_path` set)

### Jobs (Admin / Recruiter / HiringManager)

#### `GET /jobs/`

- **What it does:** Lists jobs (newest first).
- **Auth:** `Admin`, `Recruiter`, `HiringManager`.
- **Response:** `list[JobRead]`

#### `POST /jobs/`

- **What it does:** Creates a job owned by the current user and sets required skills (with optional weights).
- **Auth:** `Admin`, `Recruiter`, `HiringManager`.
- **Request (JSON):** `JobCreate`
  - `title`, `description` (optional)
  - `skills`: list of `{ "skill_id": <uuid>, "weight": <float|null> }`
- **Response:** `JobRead`

#### `GET /jobs/{job_id}`

- **What it does:** Gets a job by UUID.
- **Auth:** `Admin`, `Recruiter`, `HiringManager`.
- **Path params:** `job_id` (UUID)
- **Response:** `JobRead`

#### `PATCH /jobs/{job_id}`

- **What it does:** Updates job fields and/or replaces skill list.
- **Auth:** `Admin`, `Recruiter`, `HiringManager`.
- **Path params:** `job_id` (UUID)
- **Request (JSON):** `JobUpdate` (any subset)
  - `title`, `description`, `skills`
- **Response:** `JobRead`

#### `DELETE /jobs/{job_id}`

- **What it does:** Deletes a job.
- **Auth:** `Admin`, `Recruiter`, `HiringManager`.
- **Path params:** `job_id` (UUID)
- **Response:** `204 No Content`

### Match Scores (Admin / Recruiter / HiringManager)

Match scores are stored in `match_scores` and are unique per `(candidate_id, job_id)`.

#### `POST /matches/`

- **What it does:** Upserts a match score for a candidate + job.
- **Auth:** `Admin`, `Recruiter`, `HiringManager`.
- **Request (JSON):** `MatchScoreUpsert`
  - `candidate_id` (UUID)
  - `job_id` (UUID)
  - `score` (0–100)
  - `explanation` (optional JSON object)
- **Response:** `MatchScoreRead`

#### `POST /matches/auto-score`

- **What it does:** Computes a simple weighted skill-overlap score and upserts it into `match_scores`.
- **Auth:** `Admin`, `Recruiter`, `HiringManager`.
- **Request (JSON):**
  - `{ "candidate_id": "...", "job_id": "..." }`
- **Response:** `MatchScoreRead` (includes generated `explanation`)

#### `GET /matches/by-job/{job_id}`

- **What it does:** Lists match scores for a specific job ordered by score desc.
- **Auth:** `Admin`, `Recruiter`, `HiringManager`.
- **Path params:** `job_id` (UUID)
- **Response:** `list[MatchScoreRead]`

#### `GET /matches/by-candidate/{candidate_id}`

- **What it does:** Lists match scores for a specific candidate ordered by score desc.
- **Auth:** `Admin`, `Recruiter`, `HiringManager`.
- **Path params:** `candidate_id` (UUID)
- **Response:** `list[MatchScoreRead]`

#### `GET /matches/top-candidates/{job_id}?limit=10`

- **What it does:** Returns the top match scores for a job (highest scoring candidates).
- **Auth:** `Admin`, `Recruiter`, `HiringManager`.
- **Query params:** `limit` (1–100, default 10)
- **Response:** `list[MatchScoreRead]`

#### `GET /matches/top-jobs/{candidate_id}?limit=10`

- **What it does:** Returns the top match scores for a candidate (best matching jobs).
- **Auth:** `Admin`, `Recruiter`, `HiringManager`.
- **Query params:** `limit` (1–100, default 10)
- **Response:** `list[MatchScoreRead]`

### Live API docs

- Swagger UI: `GET /docs`
- OpenAPI JSON: `GET /openapi.json`

# AI-Powered-Hiring-Intelligence-System
