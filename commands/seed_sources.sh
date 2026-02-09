#!/usr/bin/env sh
set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "Starting database seeding..."

python -m scripts.seed_sources

echo "Database seeding finished successfully."
