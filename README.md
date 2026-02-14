# GapSense Platform

**AI-Powered Foundational Learning Diagnostic Platform for Ghana**

[![License](https://img.shields.io/badge/license-Proprietary-red.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

---

## Overview

GapSense identifies root learning gaps in Ghanaian primary and JHS students using AI-powered diagnostic reasoning, then engages parents via WhatsApp with dignity-preserving, evidence-based activities.

**The Problem:** 84% of Ghanaian children aged 7-14 lack foundational numeracy (UNICEF MICS 2023).

**The Solution:** An AI that extracts diagnostic intelligence from existing artifacts (exercise books, classroom conversations) without adding another test.

---

## Key Features

- ✅ **Adaptive Diagnostic Engine** - Traces backward through prerequisite graph to find root gaps
- ✅ **Exercise Book Analysis** - AI analyzes photos of student work for error patterns
- ✅ **WhatsApp Parent Engagement** - Dignity-first messaging (Wolf/Aurino research-based)
- ✅ **Teacher Conversation Partner** - Actionable insights, not just reports
- ✅ **NaCCA-Aligned** - Ghana curriculum (35 nodes, 6 cascade failure paths)
- ✅ **Multi-Language** - Twi, Ewe, Ga, Dagbani, English

---

## Architecture

```
WhatsApp → API → SQS Queue → Worker → Claude AI → PostgreSQL
                                   ↓
                           GUARD-001 Compliance
                                   ↓
                              WhatsApp Send
```

**Stack:**
- **Backend**: FastAPI (Python 3.12), async everywhere
- **Database**: PostgreSQL 16 (RDS)
- **AI**: Anthropic Claude Sonnet 4.5 / Haiku 4.5
- **Queue**: AWS SQS FIFO
- **Messaging**: WhatsApp Cloud API (direct)
- **Infrastructure**: AWS (Cape Town region - 50ms to Ghana)

---

## Project Structure

```
gapsense-platform/
├── src/gapsense/              # Application code
│   ├── core/                  # Models, schemas, config
│   ├── curriculum/            # Prerequisite graph, traversal
│   ├── diagnostic/            # Diagnostic engine
│   ├── engagement/            # Parent WhatsApp engagement
│   ├── webhooks/              # WhatsApp webhook handlers
│   ├── teachers/              # Teacher reports
│   ├── analytics/             # Aggregation
│   └── ai/                    # Anthropic integration
├── tests/                     # Test suite
├── infrastructure/            # AWS CDK
├── migrations/                # Alembic database migrations
├── data/                      # Non-proprietary seed data
└── docs/                      # Documentation
```

**Note:** Proprietary IP (prerequisite graph, prompts) lives in separate **gapsense-data** private repo.

---

## Quick Start

### Prerequisites

- Python 3.12+
- Docker & Docker Compose
- Poetry (Python dependency management)
- Access to `gapsense-data` repo

### Local Development

```bash
# 1. Clone repos (platform + data)
git clone https://github.com/ma-za-kpe/gapsense-platform.git
cd gapsense-platform

# Clone data repo (sibling directory)
cd ..
git clone https://github.com/ma-za-kpe/gapsense-data.git  # Private repo
cd gapsense-platform

# 2. Run setup script
./scripts/setup.sh
# This will:
# - Install Poetry if needed
# - Install dependencies
# - Create .env file
# - Verify gapsense-data repo exists

# 3. Edit .env with your API keys
nano .env

# 4. Start services
docker-compose up -d postgres

# 5. Run migrations
./scripts/migrate.sh up

# 6. Load curriculum data
poetry run python scripts/load_curriculum.py

# 7. Verify everything works (linting, tests, type checking)
./scripts/verify.sh

# 8. Start development server
./scripts/run_dev.sh

# API will be available at:
# - API: http://localhost:8000
# - Docs: http://localhost:8000/docs
# - Health: http://localhost:8000/health
```

---

## Development Workflow

### Running Tests

```bash
# All tests
poetry run pytest

# Unit tests only
poetry run pytest tests/unit -v

# Integration tests
poetry run pytest tests/integration -v

# With coverage
poetry run pytest --cov=src/gapsense --cov-report=html
```

### Code Quality

```bash
# Format
poetry run ruff format src/

# Lint
poetry run ruff check src/ --fix

# Type check
poetry run mypy src/gapsense --strict

# Run all checks
poetry run pre-commit run --all-files
```

### Git Hooks

**Automated quality checks run on every commit and push.**

#### Setup (Automatic)

Git hooks are installed automatically when you run `./scripts/setup.sh`.

#### Manual Installation

```bash
# Install pre-commit hooks
poetry run pre-commit install

# Install pre-push hooks
poetry run pre-commit install --hook-type pre-push
```

#### What Hooks Do

**On Every Commit** (fast checks ~10 seconds):
- ✅ Ruff linting (auto-fixes safe issues)
- ✅ Ruff formatting
- ✅ Trailing whitespace fix
- ✅ YAML/JSON/TOML validation
- ✅ **Detect secrets** (API keys, tokens, passwords)
- ✅ **Private key detection** (SSH, PGP keys)
- ✅ **Merge conflict markers**
- ✅ **No direct commits to main branch**

**Before Every Push** (thorough checks ~45 seconds):
- ✅ MyPy type checking (full project)
- ✅ Pytest all tests with coverage (≥80% required)
- ✅ Alembic migration check
- ✅ **Bandit security scan** (CRITICAL for student data protection)
- ✅ **Safety vulnerability check** (dependency vulnerabilities)
- ✅ **Vulture dead code detection** (unused code)
- ✅ **Deptry dependency analysis** (unused/missing dependencies)

#### Testing Hooks Manually

```bash
# Test all hooks without committing
./scripts/test_hooks.sh

# Test specific hooks
poetry run pre-commit run ruff --all-files                # Linting
poetry run pre-commit run detect-secrets --all-files      # Secret detection
poetry run pre-commit run mypy-full --all-files           # Type checking
poetry run pre-commit run pytest-coverage --all-files     # Tests + coverage
poetry run pre-commit run bandit --all-files              # Security scan
poetry run pre-commit run safety --all-files              # Vulnerability check
poetry run pre-commit run vulture --all-files             # Dead code detection
poetry run pre-commit run deptry --all-files              # Dependency analysis
```

#### Bypassing Hooks (Use Sparingly)

```bash
# Skip pre-commit hooks (emergency only)
git commit --no-verify -m "WIP: broken, will fix"

# Skip specific hook
SKIP=mypy git commit -m "Skip type checking"

# Skip pre-push hooks (DANGEROUS)
git push --no-verify
```

**When to use `--no-verify`:**
- ✅ Emergency hotfix (production down)
- ✅ Saving WIP at end of day
- ❌ **NEVER** because "tests are annoying"
- ❌ **NEVER** as regular practice

### Database Migrations

```bash
# Helper script (recommended)
./scripts/migrate.sh create "description"  # Create migration
./scripts/migrate.sh up                    # Apply migrations
./scripts/migrate.sh down                  # Rollback one
./scripts/migrate.sh status                # Check status
./scripts/migrate.sh history               # View history
./scripts/migrate.sh reset                 # DANGER: Reset all

# Direct Alembic commands (if needed)
poetry run alembic revision --autogenerate -m "description"
poetry run alembic upgrade head
poetry run alembic downgrade -1
```

### Verification & Quality Checks

**Run all checks before committing:**

```bash
./scripts/verify.sh
```

This comprehensive script runs:
- ✅ **Ruff Linter** - Code quality checks
- ✅ **Ruff Formatter** - Code formatting verification
- ✅ **MyPy Type Checker** - Static type checking
- ✅ **Pytest Unit Tests** - Full test suite with coverage
- ✅ **Alembic Migration Check** - Database migration verification
- ✅ **Import Check** - Verifies all modules import correctly

**All checks must pass (green) before pushing code.**

---

## API Documentation

Once running, visit:
- **Interactive docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health check**: http://localhost:8000/v1/health

---

## Key Modules

### Diagnostic Engine (`src/gapsense/diagnostic/`)
Orchestrates adaptive diagnostic sessions using Claude AI and the prerequisite graph.

**Key algorithms:**
- Backward tracing (B5 failure → test B4 → B2 → find root gap)
- Cascade detection (55% of students: Place Value Collapse)
- Confidence scoring (≥0.80 required for diagnosis)

### Parent Engagement (`src/gapsense/engagement/`)
WhatsApp messaging with Wolf/Aurino compliance.

**Non-negotiable constraints:**
- Strength-first framing
- No deficit language ("behind", "struggling", "failing")
- 3-minute activities, household materials only
- GUARD-001 validation at temp=0.0

### AI Service (`src/gapsense/ai/`)
Anthropic Claude integration with prompt caching (90% cost reduction).

**13 prompts:**
- DIAG-001/002/003: Diagnostic reasoning
- PARENT-001/002/003: Parent messaging
- GUARD-001: Compliance validation (blocking)
- ANALYSIS-001/002: Exercise book, voice notes
- TEACHER-001/002/003: Reports, conversation

---

## Deployment

Deployed via AWS CDK to Cape Town region (af-south-1).

```bash
cd infrastructure/cdk
cdk deploy --all
```

**Infrastructure:**
- Fargate (web + worker services)
- RDS PostgreSQL 16
- SQS FIFO queues
- S3 (media storage)
- Cognito (auth)
- ALB (load balancing)

---

## Security & Privacy

**Ghana Data Protection Act Compliance:**
- ✅ Minimal data collection (no last names, addresses, IDs)
- ✅ Encryption at rest (RDS, S3) and in transit (TLS 1.3)
- ✅ No PII in logs
- ✅ Right to deletion
- ✅ 2-year retention, then anonymize

**Proprietary IP Protection:**
- Separate `gapsense-data` repo (private)
- Pre-commit hooks block sensitive files
- Aggressive .gitignore

---

## Contributing

This is proprietary software. Internal team only.

**Code standards:**
- Follow `CODING_STANDARDS.md`
- Test critical paths (GUARD-001, graph traversal)
- Type hints on all functions (MyPy strict)
- Semantic commits

---

## License

Proprietary - Licensed to ViztaEdu under GapSense Partnership Agreement.

---

## Support

- **Documentation**: `docs/`
- **Issues**: Internal tracker
- **Contact**: maku@gapsense.app

---

## Acknowledgments

- **UNICEF StartUp Lab Cohort 6** - Technical validation & pilot funding
- **ViztaEdu** - Partnership & distribution
- **NaCCA** - Ghana curriculum standards
- **Wolf & Aurino (2020)** - Evidence-based parent engagement research

---

**Built for Ghana. Powered by AI. Grounded in dignity.**
