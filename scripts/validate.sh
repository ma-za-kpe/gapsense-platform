#!/bin/sh
set -eu

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
pytest tests

echo "[10/11] Installable package build"
python -m build

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
