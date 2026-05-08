import time

import sqlalchemy

from src.models.db.occurrence import Occurrence
from src.repository.crud.base import BaseCRUDRepository


class OccurrenceCRUDRepository(BaseCRUDRepository[Occurrence]):
    model = Occurrence

    async def create_occurrence(
        self,
        ddr_id: str,
        ddr_date_id: str,
        occurrence_type: str,
        well_name: str | None = None,
        surface_location: str | None = None,
        section: str | None = None,
        mmd: float | None = None,
        density: float | None = None,
        notes: str | None = None,
        date: str | None = None,
        commit: bool = True,
    ) -> Occurrence:
        now = int(time.time())
        return await self.create(
            {
                "ddr_id": ddr_id,
                "ddr_date_id": ddr_date_id,
                "type": occurrence_type,
                "well_name": well_name,
                "surface_location": surface_location,
                "section": section,
                "mmd": mmd,
                "density": density,
                "notes": notes,
                "date": date,
                "is_exported": False,
                "created_at": now,
                "updated_at": now,
            },
            commit=commit,
        )

    async def get_by_ddr_id(self, ddr_id: str, limit: int = 100, offset: int = 0) -> list[Occurrence]:
        stmt = sqlalchemy.select(Occurrence).where(Occurrence.ddr_id == ddr_id).limit(limit).offset(offset)
        result = await self.async_session.execute(stmt)
        return list(result.scalars().all())
