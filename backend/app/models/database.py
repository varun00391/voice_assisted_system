from sqlalchemy import event
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.models.entities import Base

# libpq-only query options that asyncpg rejects as unknown connect() arguments.
_LIBPQ_ONLY_OPTIONS = ("channel_binding", "gssencmode", "target_session_attrs")


def normalize_database_url(url: str) -> str:
    """Accept provider connection strings (postgres://…?sslmode=require) and convert them for asyncpg."""
    parsed = make_url(url)
    if parsed.drivername in ("postgres", "postgresql"):
        parsed = parsed.set(drivername="postgresql+asyncpg")
    if parsed.drivername != "postgresql+asyncpg":
        return url

    query = dict(parsed.query)
    if "sslmode" in query:
        query.setdefault("ssl", query.pop("sslmode"))
    for option in _LIBPQ_ONLY_OPTIONS:
        query.pop(option, None)
    return parsed.set(query=query).render_as_string(hide_password=False)


def create_database(url: str) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(normalize_database_url(url), pool_pre_ping=True)
    if engine.dialect.name == "sqlite":

        @event.listens_for(engine.sync_engine, "connect")
        def _enable_foreign_keys(dbapi_connection, _record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine, async_sessionmaker(engine, expire_on_commit=False)


async def init_database(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
