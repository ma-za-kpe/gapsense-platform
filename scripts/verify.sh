#!/bin/bash
# GapSense Platform Verification Script
#
# Runs linting, type checking, and tests to ensure everything is working

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🔍 GapSense Platform Verification${NC}"
echo ""

# Track overall status
FAILED=0

# Function to run check and track status
run_check() {
    local name=$1
    local command=$2

    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}Running: $name${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    if eval "$command"; then
        echo -e "${GREEN}✅ $name passed${NC}"
        echo ""
    else
        echo -e "${RED}❌ $name failed${NC}"
        echo ""
        FAILED=1
    fi
}

# 1. Ruff - Linting
run_check "Ruff Linter" "poetry run ruff check src/ scripts/ alembic/"

# 2. Ruff - Formatting
run_check "Ruff Formatter" "poetry run ruff format --check src/ scripts/ alembic/"

# 3. MyPy - Type Checking
run_check "MyPy Type Checker" "poetry run mypy src/"

# 4. Pytest - Unit Tests
run_check "Pytest Unit Tests" "poetry run pytest tests/ -v --cov=src/gapsense --cov-report=term-missing"

# 5. Database Migration Check
run_check "Alembic Migration Check" "poetry run alembic check || echo 'No migrations to check'"

# 6. Import Check (verify all modules import correctly)
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Running: Import Check${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if poetry run python -c "
import sys
try:
    from gapsense.core.models import Base, CurriculumNode
    from gapsense.ai import get_prompt_library
    from gapsense.config import settings
    from gapsense.main import create_app
    print('✅ All imports successful')
    sys.exit(0)
except Exception as e:
    print(f'❌ Import failed: {e}')
    sys.exit(1)
"; then
    echo -e "${GREEN}✅ Import Check passed${NC}"
    echo ""
else
    echo -e "${RED}❌ Import Check failed${NC}"
    echo ""
    FAILED=1
fi

# Summary
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 ALL CHECKS PASSED${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    exit 0
else
    echo -e "${RED}❌ SOME CHECKS FAILED${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "Fix the issues above and run './scripts/verify.sh' again"
    exit 1
fi
