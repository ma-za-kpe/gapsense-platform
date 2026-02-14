#!/bin/bash
# Test Git Hooks Script
#
# Manually test pre-commit hooks without actually committing
# Useful for debugging hook configuration
# Last updated: 2026-02-14

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🔍 Testing Git Hooks${NC}"
echo ""

# Detect poetry location
POETRY_CMD=""
if command -v poetry &> /dev/null; then
    POETRY_CMD="poetry"
elif [ -f "$HOME/Library/Python/3.9/bin/poetry" ]; then
    POETRY_CMD="$HOME/Library/Python/3.9/bin/poetry"
elif [ -f "$HOME/.local/bin/poetry" ]; then
    POETRY_CMD="$HOME/.local/bin/poetry"
else
    echo -e "${RED}Error: Poetry not found${NC}"
    exit 1
fi

# Check if hooks are installed
if [ ! -f ".git/hooks/pre-commit" ]; then
    echo -e "${YELLOW}⚠️  Pre-commit hooks not installed${NC}"
    echo "Run: $POETRY_CMD run pre-commit install"
    echo ""
fi

# Test pre-commit stage hooks
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Testing PRE-COMMIT Hooks (fast checks)${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if $POETRY_CMD run pre-commit run --all-files --hook-stage commit; then
    echo ""
    echo -e "${GREEN}✅ All pre-commit hooks passed${NC}"
else
    echo ""
    echo -e "${RED}❌ Some pre-commit hooks failed${NC}"
    echo "Fix the issues above and try again"
fi

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Testing PRE-PUSH Hooks (thorough checks)${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if $POETRY_CMD run pre-commit run --all-files --hook-stage push; then
    echo ""
    echo -e "${GREEN}✅ All pre-push hooks passed${NC}"
else
    echo ""
    echo -e "${RED}❌ Some pre-push hooks failed${NC}"
    echo "Fix the issues above and try again"
fi

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🎉 Hook Testing Complete${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "To run specific hooks:"
echo "  $POETRY_CMD run pre-commit run ruff --all-files"
echo "  $POETRY_CMD run pre-commit run ruff-format --all-files"
echo "  $POETRY_CMD run pre-commit run mypy-full --all-files"
echo "  $POETRY_CMD run pre-commit run pytest-coverage --all-files"
echo "  $POETRY_CMD run pre-commit run alembic-check --all-files"
echo ""
echo "To skip hooks when committing:"
echo "  git commit --no-verify -m 'message'"
echo ""
