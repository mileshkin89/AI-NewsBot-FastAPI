#!/usr/bin/env sh
set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "Cleaning all sources from the database..."

python -m scripts.clean_sources

echo "Clean sources finished successfully."
