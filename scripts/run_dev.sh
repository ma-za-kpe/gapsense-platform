#!/bin/bash
# Development Server Runner

set -e

# Colors
GREEN='\033[0;32m'
NC='\033[0m'

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
