#!/bin/bash
# GapSense Platform Setup Script
#
# Installs dependencies and sets up development environment

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🚀 Setting up GapSense Platform${NC}"
echo ""

# Check Python version
echo -e "${GREEN}Checking Python version...${NC}"
python_version=$(python3 --version | cut -d' ' -f2)
required_version="3.12"

if [[ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]]; then
    echo -e "${RED}Error: Python $required_version or higher required (found $python_version)${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Python $python_version${NC}"

# Check if Poetry is installed
if ! command -v poetry &> /dev/null; then
    echo -e "${YELLOW}Poetry not found. Installing...${NC}"
    curl -sSL https://install.python-poetry.org | python3 -
    export PATH="$HOME/.local/bin:$PATH"
fi
echo -e "${GREEN}✅ Poetry installed${NC}"

# Install dependencies
echo -e "${GREEN}Installing dependencies...${NC}"
poetry install --no-root
echo -e "${GREEN}✅ Dependencies installed${NC}"

# Check for gapsense-data repo
echo -e "${GREEN}Checking for gapsense-data repo...${NC}"
if [ ! -d "../gapsense-data" ]; then
    echo -e "${RED}Error: gapsense-data repo not found at ../gapsense-data${NC}"
    echo "Please clone gapsense-data repo or set GAPSENSE_DATA_PATH in .env"
    exit 1
fi
echo -e "${GREEN}✅ gapsense-data repo found${NC}"

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo -e "${GREEN}Creating .env file...${NC}"
    cp .env.example .env
    echo -e "${YELLOW}⚠️  Please update .env with your configuration${NC}"
fi

# Setup pre-commit hooks
echo -e "${GREEN}Setting up git hooks...${NC}"

# Detect poetry location
POETRY_CMD=""
if command -v poetry &> /dev/null; then
    POETRY_CMD="poetry"
elif [ -f "$HOME/Library/Python/3.9/bin/poetry" ]; then
    POETRY_CMD="$HOME/Library/Python/3.9/bin/poetry"
elif [ -f "$HOME/.local/bin/poetry" ]; then
    POETRY_CMD="$HOME/.local/bin/poetry"
fi

if [ -n "$POETRY_CMD" ]; then
    # Install pre-commit hooks
    $POETRY_CMD run pre-commit install 2>&1 | grep -v "^pre-commit installed" || true
    $POETRY_CMD run pre-commit install --hook-type pre-push 2>&1 | grep -v "^pre-commit installed" || true
    echo -e "${GREEN}✅ Git hooks installed (pre-commit + pre-push)${NC}"
    echo -e "${YELLOW}   Hooks will run automatically on commit and push${NC}"
else
    echo -e "${YELLOW}⚠️  Poetry not found - skipping git hooks setup${NC}"
    echo -e "${YELLOW}   Run manually: poetry run pre-commit install${NC}"
fi

echo ""
echo -e "${GREEN}✅ Setup complete!${NC}"
echo ""
echo "Next steps:"
echo "  1. Update .env with your configuration"
echo "  2. Start PostgreSQL: docker-compose up -d postgres"
echo "  3. Run migrations: ./scripts/migrate.sh up"
echo "  4. Load curriculum: python scripts/load_curriculum.py"
echo "  5. Start dev server: ./scripts/run_dev.sh"
echo ""
echo "Run './scripts/verify.sh' to check everything is working"
