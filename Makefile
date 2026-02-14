ENV_FILE=.env

# ============================================
# Help
# ============================================

help: ## Show this help
	@printf "\n"
	@printf "Available commands:\n"
	@awk '\
	/^# =+/ { getline; sub(/\r$$/,"", $$0); if ($$0 ~ /^# /) { gsub(/^# */,"", $$0); if($$0) printf "\n\033[1;34m%s:\033[0m\n", $$0 } } \
	/^[a-zA-Z0-9_.-]+:.*##/ { sub(/\r$$/,"", $$0); split($$0,a,":"); split($$0,b,"## *"); printf "  \033[36m%-25s\033[0m %s\n", a[1], b[2] }' $(MAKEFILE_LIST)
	@printf "\n"

# ============================================
# Service Management
# ============================================

build: ## Build docker containers
	docker compose --env-file $(ENV_FILE) build

up: ## Start all services
	docker compose --env-file $(ENV_FILE) up -d
# http://localhost:8000/

down:  ## Stop all services
	docker compose --env-file $(ENV_FILE) down

logs:  ## Show container logs
	docker compose --env-file $(ENV_FILE) logs -f

restart:  ## Restart services (down, build, up)
	make down && make build && make up

# ============================================
# Migration Commands
# ============================================

create-migration: ## Create Alembic migration (use: make create-migration msg="add users table")
	@test -n "$(msg)" || (echo "Usage: make create-migration msg=\"your message\"" && exit 1)
	@ENV_FILE=$(ENV_FILE) sh commands/create_migration.sh "$(msg)"

migrate: ## Apply Alembic migrations
	@echo "========================================="
	@echo "Applying database migrations..."
	@echo "========================================="
	@echo "Starting database..."
	@docker compose --env-file $(ENV_FILE) up -d --wait --wait-timeout 60 db
	@echo "Applying migrations..."
	@docker compose --env-file $(ENV_FILE) run --rm migrator sh /app/commands/run_migration.sh
	@echo "Stopping database..."
	@docker compose --env-file $(ENV_FILE) stop db
	@echo "========================================="
	@echo "Migrations completed!"
	@echo "========================================="

# ============================================
# Database Source Seeding Commands
# ============================================

seed-sources: ## Populate database with source data
	@echo "========================================="
	@echo "Database Full Seeding Process"
	@echo "========================================="
	@echo "Starting database..."
	@docker compose --env-file $(ENV_FILE) up -d --wait --wait-timeout 60 db
	@echo "Running full database seeding..."
	@docker compose --env-file $(ENV_FILE) run --rm web sh /app/commands/seed_sources.sh
	@echo "Stopping database..."
	@docker compose --env-file $(ENV_FILE) stop db
	@echo "========================================="
	@echo "Database seeding completed!"
	@echo "========================================="

clean-sources: ## Remove all sources from the database (and related news_items/posts)
	@echo "========================================="
	@echo "Cleaning all sources from the database"
	@echo "========================================="
	@echo "Starting database..."
	@docker compose --env-file $(ENV_FILE) up -d --wait --wait-timeout 60 db
	@echo "Running clean_sources script..."
	@docker compose --env-file $(ENV_FILE) run --rm web sh /app/commands/clean_sources.sh
	@echo "Stopping database..."
	@docker compose --env-file $(ENV_FILE) stop db
	@echo "========================================="
	@echo "Clean sources completed!"
	@echo "========================================="

# ============================================
# Create Superadmin Commands
# ============================================

create_superadmin: ## Create superadmin user
	@echo "========================================="
	@echo "Creating superadmin..."
	@echo "========================================="
	@echo "Starting database..."
	@docker compose --env-file $(ENV_FILE) up -d --wait --wait-timeout 60 db
	@echo "Running create_superadmin script:"
	@docker compose --env-file $(ENV_FILE) run --rm -it web sh /app/commands/create_superadmin.sh
	@echo "Stopping database..."
	@docker compose --env-file $(ENV_FILE) stop db
	@echo "========================================="
	@echo "Superadmin creation completed!"
	@echo "========================================="
