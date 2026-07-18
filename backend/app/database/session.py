from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings
from app.database.url import normalize_asyncpg_url


AsyncSessionFactory = async_sessionmaker[AsyncSession]


def create_database_engine(settings: Settings) -> AsyncEngine:
    return create_async_engine(
        normalize_asyncpg_url(settings.database_url),
        echo=settings.database_echo,
        pool_pre_ping=True,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_timeout=settings.database_pool_timeout,
    )


def create_session_factory(engine: AsyncEngine) -> AsyncSessionFactory:
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    session_factory: AsyncSessionFactory | None = getattr(
        request.app.state,
        "session_factory",
        None,
    )
    if session_factory is None:
        raise RuntimeError("Database session factory is not initialized")

    async with session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
