#!/bin/bash
# Database Migration Helper Script

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

function print_help() {
    echo "Usage: ./scripts/migrate.sh [command]"
    echo ""
    echo "Commands:"
    echo "  create <message>  - Create new migration with autogenerate"
    echo "  up                - Apply all pending migrations"
    echo "  down              - Rollback one migration"
    echo "  status            - Show current migration status"
    echo "  history           - Show migration history"
    echo "  reset             - DANGER: Reset database (drop all, recreate)"
    echo ""
    echo "Examples:"
    echo "  ./scripts/migrate.sh create 'add user preferences'"
    echo "  ./scripts/migrate.sh up"
    echo "  ./scripts/migrate.sh down"
}

function create_migration() {
    if [ -z "$1" ]; then
        echo -e "${RED}Error: Migration message required${NC}"
        echo "Usage: ./scripts/migrate.sh create 'message'"
        exit 1
    fi

    echo -e "${GREEN}Creating migration: $1${NC}"
    alembic revision --autogenerate -m "$1"

    echo -e "${YELLOW}⚠️  Review the migration file before applying!${NC}"
    echo "Migration files: alembic/versions/"
}

function upgrade() {
    echo -e "${GREEN}Applying migrations...${NC}"
    alembic upgrade head
    echo -e "${GREEN}✅ Migrations applied${NC}"
}

function downgrade() {
    echo -e "${YELLOW}⚠️  Rolling back last migration...${NC}"
    alembic downgrade -1
    echo -e "${GREEN}✅ Rollback complete${NC}"
}

function status() {
    echo -e "${GREEN}Current migration status:${NC}"
    alembic current
    echo ""
    echo -e "${GREEN}Pending migrations:${NC}"
    alembic heads
}

function history() {
    echo -e "${GREEN}Migration history:${NC}"
    alembic history --verbose
}

function reset_db() {
    echo -e "${RED}⚠️  DANGER: This will DROP ALL TABLES${NC}"
    read -p "Are you sure? Type 'yes' to confirm: " confirm

    if [ "$confirm" != "yes" ]; then
        echo "Aborted."
        exit 0
    fi

    echo -e "${YELLOW}Downgrading to base...${NC}"
    alembic downgrade base

    echo -e "${GREEN}Re-applying all migrations...${NC}"
    alembic upgrade head

    echo -e "${GREEN}✅ Database reset complete${NC}"
}

# Main command router
case "$1" in
    create)
        create_migration "$2"
        ;;
    up)
        upgrade
        ;;
    down)
        downgrade
        ;;
    status)
        status
        ;;
    history)
        history
        ;;
    reset)
        reset_db
        ;;
    *)
        print_help
        ;;
esac
