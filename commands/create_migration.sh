#!/usr/bin/env sh
set -e

# Переход в корень проекта (для вызова docker compose)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

ENV_FILE="${ENV_FILE:-.env}"
MSG="$1"

if [ -z "$MSG" ]; then
    echo "Usage: create_migration.sh <migration message>"
    echo "Example: create_migration.sh \"add users table\""
    exit 1
fi

# Остановка и отключение контейнеров при выходе из скрипта (успех или ошибка)
cleanup() {
    echo "Stopping containers..."
    docker compose --env-file "$ENV_FILE" stop web db 2>/dev/null || true
}
trap cleanup EXIT

echo "========================================="
echo "Creating Alembic migration..."
echo "========================================="
echo "Starting database and web..."
docker compose --env-file "$ENV_FILE" up -d --wait --wait-timeout 60 db web
echo "Creating migration..."
docker compose --env-file "$ENV_FILE" exec web alembic revision --autogenerate -m "$MSG"
echo "========================================="
echo "Migration created!"
echo "========================================="
