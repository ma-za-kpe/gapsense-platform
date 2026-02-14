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
# 1. Clone repo
git clone https://github.com/ma-za-kpe/gapsense-platform.git
cd gapsense-platform

# 2. Set up environment
cp .env.example .env
# Edit .env with your API keys

# 3. Set data path
export GAPSENSE_DATA_PATH=/path/to/gapsense-data

# 4. Install dependencies
poetry install

# 5. Start services
docker compose up -d

# 6. Run migrations
poetry run alembic upgrade head

# 7. Load prerequisite graph
poetry run python scripts/load_curriculum.py

# 8. Run tests
poetry run pytest

# API will be available at http://localhost:8000
# Docs at http://localhost:8000/docs
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

### Database Migrations

```bash
# Create migration
poetry run alembic revision --autogenerate -m "description"

# Apply migrations
poetry run alembic upgrade head

# Rollback
poetry run alembic downgrade -1
```

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
