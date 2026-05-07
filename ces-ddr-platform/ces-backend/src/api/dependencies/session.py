from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession as SQLAlchemyAsyncSession,
)

from src.repository.database import async_db
from src.utilities.logging.logger import logger


async def get_async_session() -> AsyncGenerator[SQLAlchemyAsyncSession, None]:
    async_session_factory = async_db.async_session_factory
    async with async_session_factory() as session:
        try:
            logger.info("Opening database session")
            yield session
        except Exception as exc:
            logger.error(f"Exception caught: {str(exc)}")
            await session.rollback()
            raise
        finally:
            logger.info("Closing database session")
