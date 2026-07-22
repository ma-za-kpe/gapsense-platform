# ============================================================================
# GapSense Dockerfile
# Multi-stage build: dev (with hot-reload) and production (optimized)
# ============================================================================

# --- Base stage ---
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=120 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_REQUESTS_MAX_RETRIES=5 \
    POETRY_INSTALLER_MAX_WORKERS=4

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir poetry==2.4.1 poetry-plugin-export==1.10.0


# --- Dev stage (hot-reload, dev dependencies) ---
FROM base AS dev

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml poetry.lock ./

RUN --mount=type=cache,target=/root/.cache/pypoetry \
    --mount=type=cache,target=/root/.cache/pip \
    poetry install --no-root

COPY . .

RUN poetry check --lock && poetry install --only-root

EXPOSE 8000


# --- Production stage (optimized, no dev deps) ---
FROM base AS production

COPY pyproject.toml poetry.lock ./

RUN --mount=type=cache,target=/root/.cache/pypoetry \
    --mount=type=cache,target=/root/.cache/pip \
    poetry install --no-root --only main

COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini ./
COPY README.md ./

RUN poetry check --lock && poetry install --only-root

# Non-root user for security
RUN useradd -m -r gapsense && chown -R gapsense:gapsense /app
USER gapsense

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/v1/health/ready || exit 1

# Default: run web service. Override for worker.
CMD ["uvicorn", "gapsense.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
