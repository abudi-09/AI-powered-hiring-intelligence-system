
# AI Powered Hiring Intelligence System

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
git clone https://github.com/<your-username>/AI-powered-hiring-intelligence-systems.git
cd AI-powered-hiring-intelligence-systems
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
# AI-Powered-Hiring-Intelligence-Systems


