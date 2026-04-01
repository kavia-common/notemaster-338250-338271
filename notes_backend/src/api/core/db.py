from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from src.api.core.config import get_settings

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


# PUBLIC_INTERFACE
def get_engine() -> AsyncEngine:
    """Get (or create) the global Async SQLAlchemy engine.

    Contract:
    - Inputs: environment variables via get_settings()
    - Output: AsyncEngine singleton
    - Errors: propagates configuration errors as ValueError
    - Side effects: creates a connection pool on first call
    """
    global _engine, _sessionmaker
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.sqlalchemy_async_database_url,
            pool_pre_ping=True,
        )
        _sessionmaker = async_sessionmaker(bind=_engine, expire_on_commit=False)
    return _engine


# PUBLIC_INTERFACE
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an AsyncSession.

    Yields:
        AsyncSession: SQLAlchemy async session.

    Notes:
        The session is closed after the request finishes.
    """
    if _sessionmaker is None:
        get_engine()
    assert _sessionmaker is not None
    async with _sessionmaker() as session:
        yield session
