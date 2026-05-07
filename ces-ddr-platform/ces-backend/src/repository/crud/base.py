import typing
from typing import Any, Generic, TypeVar

import sqlalchemy
from sqlalchemy.ext.asyncio import AsyncSession as SQLAlchemyAsyncSession
from sqlalchemy.orm import DeclarativeBase

ModelType = TypeVar("ModelType", bound=DeclarativeBase)


class BaseCRUDRepository(Generic[ModelType]):
    model: type[ModelType]

    def __init__(self, async_session: SQLAlchemyAsyncSession):
        self.async_session = async_session

    async def create(self, values: dict[str, Any]) -> ModelType:
        record = self.model(**values)
        self.async_session.add(record)
        await self.async_session.commit()
        await self.async_session.refresh(record)
        return record

    async def read_by_id(self, record_id: Any) -> ModelType | None:
        return await self.async_session.get(self.model, record_id)

    async def read_many(self, limit: int = 100, offset: int = 0) -> typing.Sequence[ModelType]:
        stmt = sqlalchemy.select(self.model).limit(limit).offset(offset)
        query = await self.async_session.execute(stmt)
        return query.scalars().all()

    async def update(self, record: ModelType, values: dict[str, Any]) -> ModelType:
        for field, value in values.items():
            setattr(record, field, value)
        self.async_session.add(record)
        await self.async_session.commit()
        await self.async_session.refresh(record)
        return record

    async def delete(self, record: ModelType) -> None:
        await self.async_session.delete(record)
        await self.async_session.commit()
