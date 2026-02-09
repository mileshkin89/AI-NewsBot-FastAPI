from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Generator

from sqlalchemy import create_engine, Engine
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
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    await async_engine.dispose()


@asynccontextmanager
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    if AsyncSessionLocal is None:
        raise RuntimeError("Database is not initialized")

    async with AsyncSessionLocal() as db:
        yield db


@contextmanager
def get_db_sync() -> Generator[Session, None, None]:
    if SessionLocal is None:
        raise RuntimeError("Database is not initialized")

    with SessionLocal() as db:
        yield db


async def get_db_depends() -> AsyncGenerator[AsyncSession, None]:
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
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
