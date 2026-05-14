import time
import typing

import sqlalchemy

from src.models.db.occurrence_edit import OccurrenceEdit
from src.repository.crud.base import BaseCRUDRepository


class OccurrenceEditCRUDRepository(BaseCRUDRepository[OccurrenceEdit]):
    model = OccurrenceEdit

    async def create_edit(
        self,
        occurrence_id: str,
        ddr_id: str,
        field: str,
        original_value: str | None,
        corrected_value: str | None,
        reason: str | None,
        created_by: str | None,
        commit: bool = True,
    ) -> OccurrenceEdit:
        return await self.create(
            {
                "occurrence_id": occurrence_id,
                "ddr_id": ddr_id,
                "field": field,
                "original_value": original_value,
                "corrected_value": corrected_value,
                "reason": reason,
                "created_by": created_by,
                "created_at": int(time.time()),
            },
            commit=commit,
        )

    async def list_all_descending(
        self,
        field_filter: str | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> typing.Sequence[OccurrenceEdit]:
        stmt = sqlalchemy.select(OccurrenceEdit).order_by(OccurrenceEdit.created_at.desc()).limit(limit).offset(offset)
        if field_filter is not None:
            stmt = stmt.where(OccurrenceEdit.field == field_filter)
        result = await self.async_session.execute(stmt)
        return result.scalars().all()

    async def count_since(self, since_ts: int) -> int:
        stmt = sqlalchemy.select(sqlalchemy.func.count(OccurrenceEdit.id)).where(
            OccurrenceEdit.created_at >= since_ts
        )
        result = await self.async_session.execute(stmt)
        return int(result.scalar_one() or 0)

    async def list_by_ddr_id(self, ddr_id: str) -> typing.Sequence[OccurrenceEdit]:
        stmt = (
            sqlalchemy.select(OccurrenceEdit)
            .where(OccurrenceEdit.ddr_id == ddr_id)
            .order_by(OccurrenceEdit.created_at.desc())
        )
        result = await self.async_session.execute(stmt)
        return result.scalars().all()
