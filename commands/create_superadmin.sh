#!/usr/bin/env sh
set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "Starting superuser creating..."

python -m scripts.create_superadmin
