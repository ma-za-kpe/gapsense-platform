#!/bin/sh
set -eu

# The candidate workspace is mounted read-only by the strict hook. Every tool that needs to write
# cache or evidence must use the container's ephemeral /tmp filesystem instead of weakening that
# boundary or changing the developer's working tree.
export COVERAGE_FILE="${COVERAGE_FILE:-/tmp/gapsense-coverage}"
export MYPY_CACHE_DIR="${MYPY_CACHE_DIR:-/tmp/gapsense-mypy-cache}"
export PIP_CACHE_DIR="${PIP_CACHE_DIR:-/tmp/gapsense-pip-cache}"
export POETRY_CACHE_DIR="${POETRY_CACHE_DIR:-/tmp/gapsense-poetry-cache}"
export PYTHONPYCACHEPREFIX="${PYTHONPYCACHEPREFIX:-/tmp/gapsense-pycache}"
export RUFF_CACHE_DIR="${RUFF_CACHE_DIR:-/tmp/gapsense-ruff-cache}"

mkdir -p \
  "$MYPY_CACHE_DIR" \
  "$PIP_CACHE_DIR" \
  "$POETRY_CACHE_DIR" \
  "$PYTHONPYCACHEPREFIX" \
  "$RUFF_CACHE_DIR" \
  /tmp/gapsense-build \
  /tmp/gapsense-htmlcov \
  /tmp/gapsense-pytest-cache

echo "[1/11] Dependency and package metadata consistency"
poetry check --lock
python -m pip check

echo "[2/11] Formatting"
ruff format --check .

echo "[3/11] Linting"
ruff check .

echo "[4/11] Strict typing"
mypy src tests

echo "[5/11] Secret scan of every commit candidate"
git -c safe.directory="$(pwd)" ls-files --cached --others --exclude-standard -z \
  | xargs -0 -r detect-secrets-hook

echo "[6/11] Static security analysis"
bandit -c pyproject.toml -r src

echo "[7/11] Database migration upgrade"
alembic upgrade head

echo "[8/11] Model-to-migration drift"
alembic check

echo "[9/11] Tests with mandatory line and branch coverage"
pytest \
  -o cache_dir=/tmp/gapsense-pytest-cache \
  tests

echo "[10/11] Installable package build"
python -m build --outdir /tmp/gapsense-build

echo "[11/11] Locked dependency vulnerability audit"
poetry export --with dev --format requirements.txt --output /tmp/gapsense-requirements.txt
pip-audit \
  --strict \
  --progress-spinner=off \
  --cache-dir /tmp/pip-audit \
  --timeout 30 \
  --disable-pip \
  --require-hashes \
  --requirement /tmp/gapsense-requirements.txt
