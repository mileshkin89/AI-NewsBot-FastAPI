"""Pytest configuration and shared fixtures for API route tests."""

from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from apps.api.admin.routes import admin_router
from apps.api.apps_api.routes.categories import category_router
from apps.api.apps_api.routes.posts import post_router
from apps.api.apps_api.routes.sources import source_router
from apps.api.apps_api.routes.users import user_router
from apps.api.auth.dependencies import admin_or_superadmin_required, pwd_context, superadmin_required
from apps.api.auth.routes import auth_router
from database.db import get_db_depends
from database.enams import NewsItemStatus, PostStatus, SourceType
from database.models import Base, Admin, Category, NewsItem, Post, Source, User


# In-memory SQLite engine for tests so no real PostgreSQL is required.
TEST_DATABASE_URL = "sqlite+aiosqlite://"


@pytest.fixture(scope="session")
def anyio_backend():
    """Use asyncio as the backend for pytest-asyncio."""
    return "asyncio"


@pytest.fixture(scope="session")
def test_engine():
    """Create a session-scoped async SQLite engine for tests."""
    return create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )


@pytest.fixture(scope="session")
async def _create_tables(test_engine):
    """Create all tables once per test session (session-scoped)."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


@pytest.fixture
async def db_session(test_engine, _create_tables):
    """
    Provide an async database session that rolls back after the test.
    Uses in-memory SQLite and a nested transaction so no data persists between tests.
    """
    async with test_engine.connect() as conn:
        trans = await conn.begin()
        try:
            async with AsyncSession(bind=conn, expire_on_commit=False) as session:
                yield session
        finally:
            await trans.rollback()


def _make_fake_admin() -> Admin:
    """Create a minimal Admin instance for bypassing auth in tests."""
    return Admin(
        id=1,
        email="admin@test.example",
        name="Test Admin",
        hashed_password="",
        refresh_token=None,
        is_active=True,
        is_super_admin=True,
        registered_at=datetime.now(timezone.utc),
    )


@pytest.fixture
async def app(db_session: AsyncSession):
    """
    Create a FastAPI test application with routers and dependency overrides.
    Database and auth are overridden so tests do not need real DB state or tokens.
    """
    async def override_get_db():
        yield db_session

    def override_admin():
        return _make_fake_admin()

    app = FastAPI(title="Test API")
    app.include_router(auth_router)
    app.include_router(admin_router)
    app.include_router(category_router)
    app.include_router(source_router)
    app.include_router(user_router)
    app.include_router(post_router)
    app.dependency_overrides[get_db_depends] = override_get_db
    app.dependency_overrides[admin_or_superadmin_required] = override_admin
    app.dependency_overrides[superadmin_required] = override_admin
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """HTTP client for making requests to the test application."""
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


# ---------- Data fixtures for route tests ----------


@pytest.fixture
async def category(db_session: AsyncSession) -> Category:
    """Create a single category for tests that need category data."""
    c = Category(name="Test Category", enabled=True)
    db_session.add(c)
    await db_session.flush()
    return c


@pytest.fixture
async def source(db_session: AsyncSession) -> Source:
    """Create a single source for tests that need source data."""
    s = Source(
        name="Test Source",
        type=SourceType.SITE,
        url="https://example.com/feed",
        title_selector=None,
        enabled=True,
    )
    db_session.add(s)
    await db_session.flush()
    return s


@pytest.fixture
async def news_item(db_session: AsyncSession, source: Source) -> NewsItem:
    """Create a single news item for tests that need news_item data."""
    n = NewsItem(
        title="Test News",
        url="https://example.com/1",
        raw_text="Raw content",
        published_at=datetime.now(timezone.utc),
        status=NewsItemStatus.NEW,
        source_id=source.id,
    )
    db_session.add(n)
    await db_session.flush()
    return n


@pytest.fixture
async def post(db_session: AsyncSession, news_item: NewsItem) -> Post:
    """Create a single post for tests that need post data."""
    p = Post(
        generated_text="Generated post text",
        status=PostStatus.NEW,
        news_id=news_item.id,
    )
    db_session.add(p)
    await db_session.flush()
    return p


@pytest.fixture
async def user(db_session: AsyncSession) -> User:
    """Create a single Telegram user for tests that need user data."""
    u = User(chat_id=123456789, active=True)
    db_session.add(u)
    await db_session.flush()
    return u


@pytest.fixture
async def admin_user(db_session: AsyncSession) -> Admin:
    """Create an Admin with known password for auth and admin route tests."""
    admin = Admin(
        email="admin@auth-test.example.com",
        name="Auth Test Admin",
        hashed_password=pwd_context.hash("testpass123"),
        refresh_token=None,
        is_active=True,
        is_super_admin=False,
        registered_at=datetime.now(timezone.utc),
    )
    db_session.add(admin)
    await db_session.flush()
    return admin


@pytest.fixture
async def superadmin_user(db_session: AsyncSession) -> Admin:
    """Create a superadmin in DB for testing deactivate rejection."""
    admin = Admin(
        email="super@auth-test.example.com",
        name="Super Admin",
        hashed_password=pwd_context.hash("superpass123"),
        refresh_token=None,
        is_active=True,
        is_super_admin=True,
        registered_at=datetime.now(timezone.utc),
    )
    db_session.add(admin)
    await db_session.flush()
    return admin
