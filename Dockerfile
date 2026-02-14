# ============================================================================
# GapSense Dockerfile
# Multi-stage build: dev (with hot-reload) and production (optimized)
# ============================================================================

# --- Base stage ---
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=false

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir poetry==1.8.2

COPY pyproject.toml poetry.lock* ./


# --- Dev stage (hot-reload, dev dependencies) ---
FROM base AS dev

RUN poetry install --no-root

COPY . .

RUN poetry install

EXPOSE 8000


# --- Production stage (optimized, no dev deps) ---
FROM base AS production

RUN poetry install --no-root --only main

COPY src/ ./src/
COPY data/ ./data/
COPY migrations/ ./migrations/
COPY alembic.ini .

RUN poetry install --only main

# Non-root user for security
RUN useradd -m -r gapsense && chown -R gapsense:gapsense /app
USER gapsense

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/v1/health/ready || exit 1

# Default: run web service. Override for worker.
CMD ["uvicorn", "gapsense.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
