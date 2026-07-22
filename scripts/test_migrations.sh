#!/bin/sh
set -eu

echo "GapSense: upgrading a fresh database to the latest schema"
alembic upgrade head

echo "GapSense: downgrading the fresh database to an empty schema"
alembic downgrade base

echo "GapSense: reapplying the complete migration history"
alembic upgrade head

echo "GapSense: verifying that models and the rebuilt schema agree"
alembic check
