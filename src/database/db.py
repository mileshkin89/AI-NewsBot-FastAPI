"""Database engine, session factories, and context managers for async and sync access."""
from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Generator

from sqlalchemy import create_engine, Engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine, async_sessionmaker
from sqlalchemy.orm import sessionmaker, Session

from database.models import Base
from settings import settings

# Async connection DB
async_db_url = settings.database_url
async_engine: AsyncEngine = create_async_engine(
    async_db_url,
    echo=False,
    future=True,
    pool_pre_ping=True,
    pool_recycle=300,
)
AsyncSessionLocal: sessionmaker = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Sync connection DB
sync_db_url = async_db_url.replace("postgresql+asyncpg", "postgresql")
sync_engine: Engine = create_engine(
    sync_db_url,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=300,
)
SessionLocal: sessionmaker = sessionmaker(
    bind=sync_engine,
    class_=Session,
    expire_on_commit=False,
)


async def init_db() -> None:
    """Enable required PostgreSQL extensions and create all tables."""
    async with async_engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Dispose of the async engine and its connection pool."""
    await async_engine.dispose()


@asynccontextmanager
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async session; caller must not use it after context exit."""
    if AsyncSessionLocal is None:
        raise RuntimeError("Database is not initialized")

    async with AsyncSessionLocal() as db:
        yield db


@contextmanager
def get_db_sync() -> Generator[Session, None, None]:
    """Yield a sync session; caller must not use it after context exit."""
    if SessionLocal is None:
        raise RuntimeError("Database is not initialized")

    with SessionLocal() as db:
        yield db


async def get_db_depends() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async session for FastAPI dependency injection; rollback on exception."""
    if AsyncSessionLocal is None:
        raise RuntimeError("Database is not initialized")

    async with AsyncSessionLocal() as db:
        try:
            yield db
        except Exception:
            await db.rollback()
            raise
        finally:
            await db.close()


async def reset_db() -> None:
    """Drop and recreate all tables (for tests)."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
