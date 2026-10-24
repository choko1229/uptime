from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.runtime_config import build_database_url, load_database_config


class Base(DeclarativeBase):
    pass


engine: AsyncEngine | None = None
async_session_maker: async_sessionmaker[AsyncSession] | None = None


def configure_database(database_url: str) -> None:
    global engine, async_session_maker
    engine = create_async_engine(database_url, pool_pre_ping=True)
    async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


def is_configured() -> bool:
    return async_session_maker is not None


def _load_saved_configuration() -> None:
    config = load_database_config()
    if config is not None:
        configure_database(build_database_url(config))


_load_saved_configuration()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    if async_session_maker is None:
        raise RuntimeError("Database is not configured yet; complete /setup first.")
    async with async_session_maker() as session:
        yield session
