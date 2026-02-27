# AI NewsBot (FastAPI)

Telegram bot that aggregates news from configured sources (Telegram channels and websites), deduplicates them in two stages (SimHash + semantic vector similarity), generates post text via OpenAI, and delivers personalized digests to users. Includes a REST API for managing sources, categories, users, and posts.

## ✨ Table of Contents

- [✨ Features](#-features)
- [📋 Prerequisites](#-prerequisites)
- [📦 Installation](#-installation)
- [🚀 Running](#-running)
- [✅ First-time setup summary](#-first-time-setup-summary)
- [🔌 API](#-api)
- [📁 Project structure (high level)](#-project-structure-high-level)
- [🧪 Development and testing](#-development-and-testing)
- [📜 Makefile commands (reference)](#-makefile-commands-reference)
- [🛠️ Tech Stack](#-tech-stack)
- [📄 License](#-license)

---

## ✨ Features

- **News aggregation**: Parse Telegram channels (Telethon) and websites (CSS selectors).
- **Two-stage deduplication**: Redis cache for “already seen” per source; **SimHash** (64-bit) for near-duplicate detection; **semantic (vector)** deduplication via OpenAI embeddings and pgvector (cosine similarity) for semantically similar texts.
- **AI generation**: OpenAI for embeddings (vector dedup) and Responses API to turn raw news into short posts (prompts editable via text files).
- **Telegram delivery**: Users subscribe by category; posts are sent with a configurable delay between messages per user.
- **REST API**: FastAPI app with JWT auth; admin and app endpoints for categories, sources, users, and posts.
- **Background pipeline**: Async tasks for parse → SimHash deduplicate → vector deduplicate → create posts → generate text → assign to users → publish.

## 📋 Prerequisites

- Python 3.12+
- PostgreSQL 17+ with **pgvector** extension (for semantic deduplication)
- Redis 7+
- [Telegram API](https://my.telegram.org) credentials (API ID, API hash) for the parser
- [OpenAI API key](https://platform.openai.com/api-keys)
- [Telegram Bot Token](https://t.me/BotFather) for the bot

## 📦 Installation

### 1. Clone and install dependencies

```bash
git clone https://github.com/mileshkin89/AI-NewsBot-FastAPI.git
cd AI-NewsBot-FastAPI
pip install uv
uv pip install -e .
```

### 2. Environment configuration

Copy the sample env and set your values:

```bash
cp .env.sample .env
```

Edit `.env` and fill in:

| Variable | Description |
|----------|-------------|
| `TG_API_ID`, `TG_API_HASH` | From [my.telegram.org](https://my.telegram.org) (Development tools). |
| `TG_SESSION_NAME` | Session name for Telethon (e.g. `tg_parser`). |
| `TG_TOKEN` | Bot token from [@BotFather](https://t.me/BotFather). |
| `OPENAI_API_KEY` | OpenAI API key. |
| `POSTGRES_*` | PostgreSQL connection (DB, port, user, password, host). |
| `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB` | Redis connection. |
| `SECRET_KEY`, `REFRESH_SECRET_KEY` | JWT signing keys (use long random strings in production). |
| `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS` | Token TTL. |

Optional (defaults in code): `NEWS_PARSE_LIMIT`, `PUBLISH_DELAY_SEC`, `NEWS_SEEN_CACHE_TTL_DAYS`, `SIMHASH_DEDUP_LOOKBACK_HOURS`, `SIMHASH_DEDUP_THRESHOLD`, `OPENAI_EMBEDDING_MODEL`, `SEMANTIC_DEDUP_THRESHOLD`, `SEMANTIC_DEDUP_LOOKBACK_HOURS`, `OPENAI_API_MODEL`, `PATH_TO_PROMPTS`, `PATH_TO_LOGS`, CSV paths for sources/categories.

### 3. Database and migrations

PostgreSQL must have the **pgvector** extension (for semantic deduplication). With Docker, `init.sql` or migrations can enable it; otherwise run `CREATE EXTENSION IF NOT EXISTS vector;` in your database.

With Docker (recommended for first run):

```bash
make migrate
```

Without Docker: ensure PostgreSQL (with pgvector) and Redis are running, set `POSTGRES_HOST`/`REDIS_HOST` (e.g. `localhost`), then run migrations from project root with `PYTHONPATH=src` and your env:

```bash
cd src && alembic upgrade head
```

### 4. Telethon session (for Telegram channel parsing)

Use a separate Telegram account (not your main one). One-time auth:

```bash
# From project root, with PYTHONPATH=src and .env loaded
python -m scripts.telethon_login
# or: make run-telethon-login  (if you add such target)
```

Follow prompts (phone number, code from Telegram). Session file is created under `sessions/` (or path from `TG_SESSION_DIR`).

### 5. Create superadmin and seed data (optional)

Create an admin user (for API login):

```bash
make create_superadmin
```

Seed categories and sources from CSV:

```bash
make seed-sources
```

CSV paths are set in `.env` or defaults (`data/categories.csv`, `data/sources.csv`).

## 🚀 Running

### With Docker Compose (recommended)

```bash
make build
make up
```

- API: **http://localhost:8000**
- Interactive API docs: **http://localhost:8000/docs**

Stop:

```bash
make down
```

### Local (without Docker)

Ensure PostgreSQL and Redis are running and reachable with the host/port from `.env`. From project root:

```bash
export PYTHONPATH=src
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Or run `main:app` from inside `src` with `PYTHONPATH` set so that `main` resolves to `src.main`.

## ✅ First-time setup summary

1. Copy `.env.sample` to `.env` and fill required variables.
2. Run migrations: `make migrate` (or Alembic manually).
3. Run Telethon login once: `python -m scripts.telethon_login` (session under `sessions/`).
4. (Optional) Create superadmin: `make create_superadmin`.
5. (Optional) Seed sources/categories: `make seed-sources`.
6. Start app: `make up` or `uvicorn` as above.
7. In Telegram, open your bot and send `/start`, then `/categories` to choose categories.

## 🔌 API

Base URL: `http://localhost:8000` (or your host). All app/admin endpoints require JWT: `Authorization: Bearer <access_token>`.

### Root and docs

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Health check; returns `{"message": "AI bot is running"}`. |
| `GET` | `/docs` | Swagger UI (interactive API docs). |
| `GET` | `/redoc` | ReDoc (alternative API docs). |

### Auth (no token required for login/refresh)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/auth/token` | **Login.** Body: `application/x-www-form-urlencoded` with `username` (email) and `password`. Returns `access_token` and sets `refresh_token` in HTTP-only cookie. |
| `POST` | `/auth/token/refresh` | **Refresh.** Uses `refresh_token` from cookie; returns new `access_token` and sets new refresh token in cookie. |
| `POST` | `/auth/logout` | **Logout.** Requires Bearer token. Clears refresh token in DB and deletes cookie. |

### Admins (superadmin only)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/admins` | List all admin users. |
| `POST` | `/admins` | Create admin. Body: `email`, `name`, `password`. |
| `PATCH` | `/admins/{admin_id}/deactivate` | Deactivate admin (superadmin cannot be deactivated). |
| `PATCH` | `/admins/{admin_id}/activate` | Activate admin. |

### Categories (admin or superadmin)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/categories` | List categories (paginated). Query: `enabled`, `q`, `skip`, `limit`. |
| `POST` | `/categories` | Create category. Body: `name`, `enabled`. |
| `GET` | `/categories/{category_id}` | Get category by ID. |
| `PUT` | `/categories/{category_id}` | Update category. Body: `name`, `enabled` (partial). |
| `DELETE` | `/categories/{category_id}` | Delete category. |
| `PATCH` | `/categories/{category_id}/deactivate` | Deactivate category. |
| `PATCH` | `/categories/{category_id}/activate` | Activate category. |
| `GET` | `/categories/{category_id}/sources` | List sources linked to category (paginated). Query: `enabled`, `q`, `skip`, `limit`. |
| `GET` | `/categories/{category_id}/users` | List users subscribed to category (paginated). Query: `category_enabled`, `q`, `skip`, `limit`. |

### Sources (admin or superadmin)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/sources` | List sources (paginated). Query: `enabled`, `type` (tg/site), `q`, `skip`, `limit`. |
| `POST` | `/sources` | Create source. Body: `name`, `type`, `url`, `title_selector` (optional), `enabled`. |
| `GET` | `/sources/{source_id}` | Get source by ID. |
| `PUT` | `/sources/{source_id}` | Update source. Body: `name`, `type`, `url`, `title_selector`, `enabled` (partial). |
| `DELETE` | `/sources/{source_id}` | Delete source. |
| `PATCH` | `/sources/{source_id}/deactivate` | Deactivate source. |
| `PATCH` | `/sources/{source_id}/activate` | Activate source. |
| `GET` | `/source/{source_id}/categories` | List categories assigned to source (paginated). Query: `category_enabled`, `q`, `skip`, `limit`. |

### Users (admin or superadmin)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/users` | List Telegram users (paginated). Query: `active`, `q`, `skip`, `limit`, `sort_by`, `sort_order`. |
| `GET` | `/users/{user_id}` | Get user by ID. |
| `PATCH` | `/users/{user_id}/deactivate` | Deactivate user (stops receiving posts). |
| `PATCH` | `/users/{user_id}/activate` | Activate user. |
| `DELETE` | `/users/{user_id}` | Delete user. |
| `GET` | `/users/{user_id}/categories` | List categories subscribed by user (paginated). Query: `category_enabled`, `q`, `skip`, `limit`. |

### Posts (admin or superadmin)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/posts` | List posts (paginated). Query: `status`, `q`, `date_from`, `date_to`, `skip`, `limit`, `sort_by`, `sort_order`. |
| `POST` | `/posts` | Create post. Body: `generated_text`. |
| `GET` | `/posts/{post_id}` | Get post by ID with nested `news_item`, `source`, and categories. |
| `PUT` | `/posts/{post_id}` | Update post. Body: `generated_text` (partial). |
| `DELETE` | `/posts/{post_id}` | Delete post. |

### Authentication

Use **superadmin** (or another admin) to log in: `POST /auth/token` with `username=<admin_email>` and `password=<password>`. Response contains `access_token`. Send it in the header for protected routes:

```
Authorization: Bearer <access_token>
```

Refresh token is stored in an HTTP-only cookie and used by `POST /auth/token/refresh` to get a new access token without sending password again.

## 📁 Project structure (high level)

```
<project-root>/
  .env.sample              # Sample env vars; copy to .env and fill in
  Dockerfile               # Python image, deps, app copy (for docker compose)
  docker-compose.yml       # Services: web, db, redis, migrator
  Makefile                 # build, up, down, migrate, seed-sources, create_superadmin, etc.
  pyproject.toml           # Project metadata and dependencies
  uv.lock                  # Locked dependency versions (uv)
  init.sql                 # Optional PostgreSQL init (docker-entrypoint-initdb.d)
  README.md                # This file

  commands/                # Shell scripts for Docker/make (run_migration, seed_sources, etc.)
  data/                    # CSV for initial seed: categories.csv, sources.csv
  prompts/                 # Generator prompts: system.txt, user.txt (editable without code change)
  logs/                    # App log file (e.g. app.log); created at runtime
  sessions/                # Telethon session files (*.session); created after telethon_login

  src/                     # Application code
    main.py                # FastAPI app, lifespan, mounts routers and starts bot loop
    settings.py            # Pydantic settings from env
    logging_config.py      # Logger setup
    handlers/              # Background pipeline tasks (parse, deduplicate, create/generate posts, publish)
      parse_news.py        # Parse sources, filter unseen, create news items
      deduplicate_news.py  # SimHash dedup then vector dedup (two tasks)
      create_posts.py      # Create posts for vector-deduplicated items
      generate_posts.py    # OpenAI text generation, mark GENERATED
      process_users_posts.py  # Assign posts to users, mark processed
      publish_posts.py     # Publish to Telegram with per-user delay
    database/              # Models (incl. embedding column), repository, migrations, db connection
    apps/
      api/
        apps_api/          # Public API: categories, sources, users, posts
        admin/             # Admin users management
        auth/              # JWT login, refresh, logout
      tg_bot/              # Aiogram handlers: /start, /categories, publisher
      news_parser/         # Parsers (Telegram, site), factory, schemas
      news_deduplicator/   # SimHash, vector (embedding) dedup, text normalizer
      post_generator/      # OpenAI client usage, prompts, PostGenerationService
    infrastructure/        # OpenAI client, OpenAI embeddings, Redis, Telethon, Aiogram bot instance
    scripts/               # telethon_login, create_superadmin, seed_sources, clean_sources
    tests/                 # Pytest and API/unit tests
```

## 🧪 Development and testing

Run tests (from repo root, with `PYTHONPATH=src`):

```bash
pytest src/tests -v
```

API tests use an in-memory SQLite backend; no real PostgreSQL/Redis required for the test suite.

### Prompts (post generator)

Prompt text for the AI post generator is configured by editing files in the **`prompts/`** directory:

- **`prompts/system.txt`** — system prompt (role and rules for the model).
- **`prompts/user.txt`** — user prompt (instruction for rewriting/summarizing news).

Changes take effect on the next run; no code changes or restart are required. If a file is missing or unreadable, defaults from `apps/post_generator/default_prompts.py` are used.

### Categories and sources (initial data)

The initial list of news categories and sources can be set by editing CSV files in the **`data/`** directory:

- **`data/categories.csv`** — categories (e.g. `name`, `enabled`).
- **`data/sources.csv`** — sources (URL, type: `tg` or `site`, title selector for sites, etc.).

Load them into the database with `make seed-sources`. After that, categories and sources are managed via the **REST API** (create, update, delete, list). The CSV files are only used for the initial seed.

### Site parser (adding new websites)

For website parsing there is a **base class** (`apps/news_parser/base.py` — `BaseParser`, and `apps/news_parser/sites.py` — `SiteParser`) that fetches HTML and extracts items by a CSS selector. Because **selectors differ for each site**, you need to implement a **separate parser per resource**: inherit from `BaseParser` (or `SiteParser`), override `fetch()` (and optionally `normalize()`), and register the new parser in the factory (`apps/news_parser/factory.py`) if the source type or URL pattern is different. Telegram channels use a single `TelegramParser`; sites are typically one parser class per site or per selector scheme.

## 📜 Makefile commands (reference)

| Command | Description |
|---------|-------------|
| `make help` | List available targets. |
| `make build` | Build Docker images. |
| `make up` | Start all services (web, db, redis). |
| `make down` | Stop services. |
| `make logs` | Follow container logs. |
| `make migrate` | Apply Alembic migrations. |
| `make create-migration msg="..."` | Create a new migration. |
| `make seed-sources` | Load sources/categories from CSV. |
| `make clean-sources` | Remove all sources (and related news/posts). |
| `make create_superadmin` | Create superadmin user (interactive). |

## 🛠️ Tech Stack

### Language & runtime
- **Python** (>=3.12) - Application and scripts
- **uvicorn** (>=0.40.0) - ASGI server for FastAPI

### API & bot
- **FastAPI** (>=0.128.0) - REST API, OpenAPI docs, dependency injection
- **Aiogram** (>=3.24.0) - Telegram bot (handlers, FSM, menu)

### Database
- **PostgreSQL** (17.4) - Main relational database (sources, news, posts, users, admins)
- **pgvector** - Extension for storing and querying embedding vectors (cosine distance); used for semantic deduplication
- **SQLAlchemy** (>=2.0.46) - Async ORM, sessions, models
- **asyncpg** (>=0.31.0) - Async PostgreSQL driver
- **Alembic** (>=1.18.3) - Database migrations

### Cache
- **Redis** (7.4) - Seen-news cache per source (before DB write)

### AI
- **OpenAI** (>=2.17.0) - Embeddings API (for vector deduplication) and Responses API (post text generation)

### Parsing
- **Telethon** (>=1.42.0) - Fetch messages from Telegram channels
- **requests** (>=2.32.5) - HTTP client for site sources
- **Beautiful Soup** (bs4, >=0.0.2) - HTML parsing for site sources

### Auth
- **PyJWT** (>=2.11.0) - Access and refresh tokens for API
- **passlib** (>=1.7.4) - Password hashing
- **argon2-cffi** (>=25.1.0) - Argon2 hashing for admin passwords

### ️ Config & validation
- **Pydantic** (>=2.12.5) - Request/response schemas
- **pydantic-settings** (>=2.12.0) - Load settings from env and `.env`

### Testing
- **pytest** (>=9.0.2) - Test framework
- **pytest-asyncio** (>=0.24.0) - Async test support
- **httpx** (>=0.28.0) - Async HTTP client for TestClient
- **aiosqlite** (>=0.20.0) - In-memory SQLite backend for tests

### DevOps
- **Docker** - Container runtime
- **Docker Compose** - Run app, PostgreSQL, Redis, migrator
- **uv** - Dependency manager and lock file (optional)

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
