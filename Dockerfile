FROM python:3.12-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt

COPY . .

ENV PYTHONPATH=/app \
    APP_ENV=development \
    DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/hiring \
    JWT_SECRET_KEY=replace-at-runtime

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
