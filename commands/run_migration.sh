#!/bin/sh
set -e

ALEMBIC_CONFIG="/app/alembic.ini"
MIGRATIONS_DIR="/app/src/database/migrations/versions"

echo "Starting Alembic migration process..."

# Checking the existence of the migrations directory
if [ ! -d "$MIGRATIONS_DIR" ]; then
    echo "Migrations directory does not exist."
    echo "Nothing to apply. Skipping migrations."
    exit 0
fi

# Checking for the presence of migration files
if [ -z "$(ls -A "$MIGRATIONS_DIR")" ]; then
    echo "No migration files found."
    echo "Nothing to apply. Skipping migrations."
    exit 0
fi

echo "Migration files found. Applying migrations..."

alembic -c "$ALEMBIC_CONFIG" upgrade head

echo "Migrations successfully applied."