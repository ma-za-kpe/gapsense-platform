#!/bin/bash
# Generate vercel.json from template with environment variable substitution
# Usage: ./scripts/generate-vercel-config.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TEMPLATE_FILE="$PROJECT_ROOT/vercel.json.template"
OUTPUT_FILE="$PROJECT_ROOT/vercel.json"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "📝 Generating vercel.json from template..."

# Get API_BASE_URL from environment or AWS Secrets Manager
if [ -z "$API_BASE_URL" ]; then
    echo "${YELLOW}⚠️  API_BASE_URL not set in environment${NC}"
    echo "Fetching from AWS Secrets Manager..."

    API_BASE_URL=$(aws secretsmanager get-secret-value \
        --secret-id gapsense/prod/api-base-url \
        --region us-east-1 \
        --query 'SecretString' \
        --output text | jq -r '.url')

    if [ -z "$API_BASE_URL" ]; then
        echo "❌ Failed to fetch API_BASE_URL from AWS Secrets Manager"
        echo "Using default: http://localhost:8000"
        API_BASE_URL="http://localhost:8000"
    else
        echo "${GREEN}✅ Fetched API_BASE_URL from AWS: $API_BASE_URL${NC}"
    fi
else
    echo "${GREEN}✅ Using API_BASE_URL from environment: $API_BASE_URL${NC}"
fi

# Substitute environment variables in template
sed "s|\${API_BASE_URL}|$API_BASE_URL|g" "$TEMPLATE_FILE" > "$OUTPUT_FILE"

echo "${GREEN}✅ Generated $OUTPUT_FILE${NC}"
echo ""
echo "API rewrites will proxy to: $API_BASE_URL"
