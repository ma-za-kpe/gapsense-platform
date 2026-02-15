#!/bin/bash
# Development Server Runner

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check if pre-commit hooks are installed
if [ ! -f ".git/hooks/pre-commit" ]; then
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}⚠️  WARNING: Pre-commit hooks not installed!${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "Git hooks provide security scanning, code quality checks,"
    echo "and prevent committing secrets (API keys, passwords)."
    echo ""
    echo "Install now:"
    echo "  poetry run pre-commit install"
    echo "  poetry run pre-commit install --hook-type pre-push"
    echo ""
    echo "Or run the full setup:"
    echo "  ./scripts/setup.sh"
    echo ""
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    sleep 3  # Give developer time to read the warning
fi

echo -e "${GREEN}🚀 Starting GapSense Development Server${NC}"
echo ""
echo "Environment: local"
echo "API Docs: http://localhost:8000/docs"
echo "Health: http://localhost:8000/health"
echo ""

# Run with auto-reload
python -m uvicorn gapsense.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    --log-level info
