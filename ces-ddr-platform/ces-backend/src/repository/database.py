from typing import AsyncGenerator

from pydantic import PostgresDsn
from sqlalchemy.ext.asyncio import (
    AsyncEngine as SQLAlchemyAsyncEngine,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession as SQLAlchemyAsyncSession,
)
from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
)
from sqlalchemy.ext.asyncio import (
    create_async_engine as create_sqlalchemy_async_engine,
)
from sqlalchemy.pool import Pool as SQLAlchemyPool

from src.config.manager import settings


class AsyncDatabase:
    def __init__(self):
        self.postgres_uri: str = (
            f"{settings.DB_POSTGRES_SCHEMA}://{settings.DB_POSTGRES_USERNAME}:"
            f"{settings.DB_POSTGRES_PASSWORD}@{settings.DB_POSTGRES_HOST}:"
            f"{settings.DB_POSTGRES_PORT}/{settings.DB_POSTGRES_NAME}"
        )

        self.async_engine: SQLAlchemyAsyncEngine = create_sqlalchemy_async_engine(
            url=self.set_async_db_uri,
            echo=settings.IS_DB_ECHO_LOG,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_POOL_OVERFLOW,
            pool_pre_ping=True,
            pool_recycle=3600,
            pool_timeout=30,
        )

        self.async_session: SQLAlchemyAsyncSession = SQLAlchemyAsyncSession(bind=self.async_engine)
        self.pool: SQLAlchemyPool = self.async_engine.pool

        self.async_session_factory = async_sessionmaker(
            bind=self.async_engine,
            class_=SQLAlchemyAsyncSession,
            expire_on_commit=False,
        )

    async def get_session(self) -> AsyncGenerator[SQLAlchemyAsyncSession, None]:
        async with self.async_session_factory() as session:
            yield session

    @property
    def set_async_db_uri(self) -> str | PostgresDsn:
        return (
            self.postgres_uri.replace("postgresql://", "postgresql+asyncpg://")
            if self.postgres_uri
            else self.postgres_uri
        )


async_db: AsyncDatabase = AsyncDatabase()
