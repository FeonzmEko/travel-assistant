from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from backend.config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if engine.dialect.name == "sqlite":
            for statement in (
                "ALTER TABLE trip_activities ADD COLUMN longitude FLOAT",
                "ALTER TABLE trip_activities ADD COLUMN latitude FLOAT",
            ):
                try:
                    await conn.execute(text(statement))
                except OperationalError as exc:
                    if "duplicate column" not in str(exc).lower():
                        raise
