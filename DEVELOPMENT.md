# GapSense Development Guide

Complete guide for developers to set up, run, and contribute to the GapSense Platform.

## Table of Contents

- [Project Overview](#project-overview)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Initial Setup](#initial-setup)
- [Running the Application](#running-the-application)
- [Running Tests](#running-tests)
- [Code Quality](#code-quality)
- [Git Workflow](#git-workflow)
- [Database Management](#database-management)
- [Troubleshooting](#troubleshooting)

---

## Project Overview

**GapSense** is an AI-powered foundational learning diagnostic platform for Ghana, built with:
- **FastAPI** (async Python web framework)
- **PostgreSQL 15** (database)
- **SQLAlchemy 2.0** (async ORM with greenlet)
- **Anthropic Claude** (AI question generation)
- **Poetry** (Python dependency management)
- **Docker Compose** (containerized development)

**Test Coverage:** 88% (exceeds 80% requirement)
**Total Tests:** 202 passing, 1 skipped

---

## Project Structure

```
gapsense/                          # Main application repository
├── src/gapsense/                  # Application source code
│   ├── api/v1/                   # API endpoints (curriculum, diagnostics, parents, teachers)
│   ├── core/                     # Core models, schemas, database utilities
│   ├── diagnostic/               # Adaptive diagnostic engine, gap analysis, questions
│   ├── ai/                       # AI prompt loading and management
│   └── main.py                   # FastAPI application entry point
├── tests/                         # Test suite (202 tests, 88% coverage)
│   ├── api/                      # API endpoint tests
│   ├── integration/              # Integration tests with database
│   └── unit/                     # Unit tests
├── alembic/                       # Database migrations
├── infrastructure/                # Docker, docker-compose, deployment configs
├── scripts/                       # Utility scripts (load_curriculum.py, etc.)
├── pyproject.toml                # Poetry dependencies and tool configs
├── .pre-commit-config.yaml       # Git pre-commit hooks
└── README.md                     # Project overview

gapsense-data/                     # Separate repository for curriculum data
└── curriculum/                    # NaCCA curriculum JSON files
    ├── strands.json
    ├── sub_strands.json
    ├── nodes.json
    └── prerequisites.json
```

### Should Projects Be in Same Folder?

**Recommended Setup:**
```
~/Documents/projects/
├── gapsense/                  # Main app repo (git)
└── gapsense-data/             # Curriculum data repo (separate git)
    └── curriculum/
```

**Why separate?**
- Data repo can be updated independently
- Different access controls (data may be sensitive)
- Smaller main repo for faster clones
- Data versioning separate from code versioning

**Configuration:** Set `PROMPT_LIBRARY_PATH` in `.env` to point to curriculum folder.

---

## Prerequisites

### Required Software

```bash
# 1. Python 3.12+ (we use 3.13.9)
python --version  # Should be 3.12 or higher

# 2. Poetry (dependency management)
curl -sSL https://install.python-poetry.org | python3 -
poetry --version

# 3. Docker Desktop (for PostgreSQL)
docker --version
docker-compose --version

# 4. Git
git --version
```

### Optional but Recommended

```bash
# Pre-commit (git hooks)
brew install pre-commit  # macOS
# or
pip install pre-commit

# PostgreSQL client (for debugging)
brew install postgresql@15  # macOS
```

---

## Initial Setup

### 1. Clone Repositories

```bash
# Clone main application
cd ~/Documents/projects
git clone <gapsense-repo-url>
cd gapsense

# Clone curriculum data (separate repo)
cd ~/Documents/projects
git clone <gapsense-data-repo-url>
```

### 2. Install Dependencies

```bash
cd ~/Documents/projects/gapsense

# Install Python dependencies
poetry install

# Install pre-commit hooks
poetry run pre-commit install
```

### 3. Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your settings
# Required variables:
DATABASE_URL=postgresql+asyncpg://gapsense:gapsense@localhost:5433/gapsense  # pragma: allowlist secret
ANTHROPIC_API_KEY=your-api-key-here
PROMPT_LIBRARY_PATH=/Users/yourusername/Documents/projects/gapsense-data/curriculum
DEBUG=true
ENVIRONMENT=development
```

### 4. Start Database

```bash
# Start PostgreSQL container
cd infrastructure/
docker compose up -d db

# Verify database is running
docker ps  # Should show postgres:15-alpine on port 5433
```

### 5. Run Database Migrations

```bash
# Create/update database schema
poetry run alembic upgrade head
```

### 6. Load Curriculum Data

```bash
# Load NaCCA curriculum into database
poetry run python scripts/load_curriculum.py
```

---

## Running the Application

### Development Server

```bash
# Option 1: Using Poetry
poetry run uvicorn gapsense.main:app --reload --port 8000

# Option 2: Using the virtualenv directly
~/.local/bin/poetry run uvicorn gapsense.main:app --reload --port 8000
```

**Access:**
- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health: http://localhost:8000/health

### Production Server

```bash
poetry run uvicorn gapsense.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --log-level info
```

---

## Running Tests

### Quick Test Commands

```bash
# Run all tests with coverage (202 tests)
poetry run pytest

# Run specific test file
poetry run pytest tests/api/test_parents.py

# Run specific test class
poetry run pytest tests/api/test_parents.py::TestParentCreation

# Run specific test
poetry run pytest tests/api/test_parents.py::TestParentCreation::test_create_parent_success

# Run with verbose output
poetry run pytest -v

# Run with short output (quiet)
poetry run pytest -q

# Run and see print statements
poetry run pytest -s
```

### Test Categories

```bash
# Unit tests only
poetry run pytest tests/unit/

# API tests only
poetry run pytest tests/api/

# Integration tests only
poetry run pytest tests/integration/

# Specific markers
poetry run pytest -m "not slow"
poetry run pytest -m integration
```

### Coverage Reports

```bash
# Coverage with terminal report
poetry run pytest --cov=src/gapsense --cov-report=term-missing

# Coverage with HTML report
poetry run pytest --cov=src/gapsense --cov-report=html
open htmlcov/index.html  # View in browser

# Coverage for specific module
poetry run pytest tests/api/test_parents.py --cov=src/gapsense/api/v1/parents
```

**Current Coverage: 88%** (target: 80% minimum)

### Important: Greenlet Concurrency

Our tests use async SQLAlchemy which requires greenlet concurrency tracking:

```toml
# pyproject.toml
[tool.coverage.run]
concurrency = ["greenlet"]  # ← Critical for async coverage
```

Without this, async code coverage won't be tracked correctly!

---

## Code Quality

### Pre-Commit Hooks

We use **strict pre-commit hooks** that run automatically on every commit:

```yaml
# .pre-commit-config.yaml
hooks:
  - Ruff Linter (code quality)
  - Ruff Formatter (code formatting)
  - MyPy (type checking - STRICT mode)
  - Pytest (88% coverage requirement)
  - Alembic Check (migration consistency)
  - Bandit (security scanning)
  - Safety (dependency vulnerability check)
  - Detect Secrets (credential scanning)
```

### Running Checks Manually

```bash
# Run all pre-commit hooks
pre-commit run --all-files

# Run specific hook
pre-commit run mypy --all-files
pre-commit run pytest-coverage --all-files
pre-commit run ruff --all-files

# Ruff linting
poetry run ruff check . --exclude infrastructure/

# Ruff auto-fix
poetry run ruff check --fix . --exclude infrastructure/

# MyPy type checking
poetry run mypy src/gapsense/

# Bandit security scan
poetry run bandit -r src/gapsense -c pyproject.toml
```

### Code Style Guidelines

**Type Hints (Required):**
```python
# ✅ GOOD - Full type hints
async def create_parent(
    parent_data: ParentCreate,
    db: AsyncSession = Depends(get_db)
) -> Parent:
    ...

# ❌ BAD - No type hints
async def create_parent(parent_data, db):
    ...
```

**Async/Await (Always):**
```python
# ✅ GOOD - Async database operations
async def get_parent(parent_id: UUID, db: AsyncSession) -> Parent | None:
    result = await db.execute(select(Parent).where(Parent.id == parent_id))
    return result.scalar_one_or_none()

# ❌ BAD - Sync operations
def get_parent(parent_id: UUID, db: Session) -> Parent | None:
    return db.query(Parent).filter(Parent.id == parent_id).first()
```

**Pydantic V2 (ConfigDict):**
```python
# ✅ GOOD - Pydantic V2
class ParentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    phone: str

# ❌ BAD - Pydantic V1
class ParentResponse(BaseModel):
    class Config:
        orm_mode = True
```

---

## Git Workflow

### Branch Strategy

```
main           # Production-ready code (protected)
  └─ develop   # Integration branch (protected)
      └─ feature/your-feature-name
      └─ fix/your-bugfix-name
```

### Commit Workflow

```bash
# 1. Create feature branch from develop
git checkout develop
git pull origin develop
git checkout -b feature/add-sms-notifications

# 2. Make changes and write tests
# ... code changes ...
# ... write tests achieving 80%+ coverage ...

# 3. Stage changes
git add .

# 4. Commit (pre-commit hooks will run automatically)
git commit -m "feat: Add SMS notification support

- Implement Twilio integration for SMS
- Add parent notification preferences
- Add SMS delivery tracking
- Tests: 15 new tests, 92% coverage

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# Pre-commit hooks will run:
# ✓ Ruff Linter
# ✓ Ruff Formatter
# ✓ MyPy Type Checker
# ✓ Pytest (202 tests, 88% coverage)
# ✓ Alembic Migration Check
# ✓ Bandit Security Scan
# ✓ Safety Vulnerability Check

# 5. Push to remote
git push origin feature/add-sms-notifications

# 6. Create Pull Request on GitHub
# PR will trigger CI/CD checks
```

### Commit Message Format

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: Add new feature
fix: Fix bug
docs: Update documentation
test: Add tests
refactor: Code refactoring
perf: Performance improvement
chore: Maintenance tasks
```

### Pre-Push Hooks

Additional checks run on `git push`:

```bash
# These run automatically on push:
1. MyPy (full project type check)
2. Pytest with 80% coverage requirement
3. Alembic migration consistency check
4. Bandit security scan
5. Safety vulnerability check
```

### Bypassing Hooks (Emergency Only)

```bash
# Skip pre-commit hooks (NOT RECOMMENDED)
git commit --no-verify -m "Emergency hotfix"

# Skip specific pre-push hook
SKIP=safety git push origin develop  # Only skip safety check
```

---

## Database Management

### Alembic Migrations

```bash
# Create new migration
poetry run alembic revision --autogenerate -m "Add email field to parents"

# Review migration file
# Edit: alembic/versions/xxx_add_email_field_to_parents.py

# Apply migration
poetry run alembic upgrade head

# Rollback one migration
poetry run alembic downgrade -1

# Rollback to specific revision
poetry run alembic downgrade abc123

# View migration history
poetry run alembic history

# Check current revision
poetry run alembic current

# Check if models match database
poetry run alembic check
```

### Database Reset (Development Only)

```bash
# Drop all tables and recreate
poetry run alembic downgrade base
poetry run alembic upgrade head

# Reload curriculum data
poetry run python scripts/load_curriculum.py
```

### Database Access

```bash
# Connect to PostgreSQL
psql -h localhost -p 5433 -U gapsense -d gapsense
# Password: gapsense

# Useful queries
SELECT COUNT(*) FROM curriculum_nodes;
SELECT COUNT(*) FROM parents;
SELECT * FROM diagnostic_sessions ORDER BY created_at DESC LIMIT 10;
```

---

## Troubleshooting

### Common Issues

#### 1. Database Connection Failed

```bash
# Check if database container is running
docker ps

# If not running, start it
cd infrastructure/
docker compose up -d db

# Check logs
docker compose logs db

# Verify connection
psql -h localhost -p 5433 -U gapsense -d gapsense -c "SELECT 1"
```

#### 2. Pre-Commit Hook Failures

```bash
# MyPy errors
poetry run mypy src/gapsense/  # See specific errors
# Fix type hints

# Pytest coverage below 80%
poetry run pytest --cov=src/gapsense --cov-report=term-missing
# Write more tests

# Ruff formatting issues
poetry run ruff check --fix .  # Auto-fix

# Alembic migration issues
poetry run alembic check  # See what's out of sync
poetry run alembic revision --autogenerate -m "Fix sync"
```

#### 3. Tests Failing Locally

```bash
# Clear pytest cache
rm -rf .pytest_cache
rm -rf htmlcov

# Ensure database is clean
poetry run alembic downgrade base
poetry run alembic upgrade head

# Run tests in verbose mode
poetry run pytest -vv --tb=short

# Run single failing test
poetry run pytest tests/api/test_parents.py::TestParentCreation::test_create_parent_success -vv --tb=short
```

#### 4. Import Errors

```bash
# Ensure you're in poetry shell or using poetry run
poetry shell

# Or prefix all commands with:
poetry run <command>

# Check Python path
poetry run python -c "import sys; print(sys.path)"
```

#### 5. Coverage Not Tracking Async Code

**Problem:** Coverage shows 0% for async SQLAlchemy code

**Solution:** Ensure `concurrency = ["greenlet"]` in `pyproject.toml`:

```toml
[tool.coverage.run]
source = ["src/gapsense"]
concurrency = ["greenlet"]  # ← This is critical!
```

#### 6. Port Already in Use

```bash
# Check what's using port 8000
lsof -i :8000

# Kill process
kill -9 <PID>

# Or use different port
poetry run uvicorn gapsense.main:app --port 8001
```

---

## Development Best Practices

### Writing Tests

**Test Structure:**
```python
# tests/api/test_parents.py
class TestParentCreation:
    """Test parent creation endpoint."""

    async def test_create_parent_success(
        self, client: AsyncClient, test_district
    ) -> None:
        """Test successful parent creation with all fields."""
        # Arrange
        parent_data = {
            "phone": "+233501234567",
            "preferred_name": "Auntie Ama",
            "district_id": test_district.id,
        }

        # Act
        response = await client.post("/api/v1/parents/", json=parent_data)

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["phone"] == parent_data["phone"]
```

**Test Coverage Requirements:**
- Overall: ≥80% (currently 88%)
- New files: ≥80%
- Test ALL code paths:
  - ✅ Happy path
  - ✅ Error cases
  - ✅ Edge cases
  - ✅ Validation failures
  - ✅ Database constraints

### Adding New Endpoints

1. **Create Schema** (`src/gapsense/core/schemas/`)
2. **Add Endpoint** (`src/gapsense/api/v1/`)
3. **Write Tests** (`tests/api/`)
4. **Run Coverage** (ensure ≥80%)
5. **Update Docs** (OpenAPI auto-generated)

### Working with AI Prompts

```bash
# Prompts are loaded from:
PROMPT_LIBRARY_PATH=/path/to/gapsense-data/curriculum

# Test prompt loading:
poetry run python -c "
from gapsense.ai import get_prompt_library
lib = get_prompt_library()
print(f'Loaded {len(lib)} prompts')
print(lib.get_prompt('DIAG-001'))
"
```

---

## Additional Resources

- **API Documentation:** http://localhost:8000/docs
- **Anthropic Claude API:** https://docs.anthropic.com
- **FastAPI Docs:** https://fastapi.tiangolo.com
- **SQLAlchemy 2.0:** https://docs.sqlalchemy.org/en/20/
- **Pydantic V2:** https://docs.pydantic.dev/latest/
- **Alembic:** https://alembic.sqlalchemy.org

---

## Quick Reference

### Essential Commands

```bash
# Start development
docker compose up -d db
poetry run uvicorn gapsense.main:app --reload

# Run tests
poetry run pytest

# Code quality
poetry run ruff check --fix .
poetry run mypy src/gapsense/

# Database
poetry run alembic upgrade head
poetry run python scripts/load_curriculum.py

# Git workflow
git checkout -b feature/my-feature
git add .
git commit -m "feat: Add feature"
git push origin feature/my-feature
```

### File Locations

- **Config:** `src/gapsense/config.py`
- **Database:** `src/gapsense/core/database.py`
- **Models:** `src/gapsense/core/models/`
- **Schemas:** `src/gapsense/core/schemas/`
- **API Routes:** `src/gapsense/api/v1/`
- **Tests:** `tests/`
- **Migrations:** `alembic/versions/`

---

## Getting Help

1. **Check this guide first**
2. **Review test files** for examples
3. **Check API docs** at /docs endpoint
4. **Ask the team** in Slack/Discord
5. **Open an issue** on GitHub

---

**Happy Coding! 🚀**
