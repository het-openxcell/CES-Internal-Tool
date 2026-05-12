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

    async def delete_by_ddr_id(self, ddr_id: str) -> None:
        stmt = sqlalchemy.delete(Occurrence).where(Occurrence.ddr_id == ddr_id)
        await self.async_session.execute(stmt)
        await self.async_session.commit()

    async def replace_for_ddr(self, ddr_id: str, occurrences: list[dict]) -> None:
        stmt = sqlalchemy.delete(Occurrence).where(Occurrence.ddr_id == ddr_id)
        await self.async_session.execute(stmt)
        if occurrences:
            now = int(time.time())
            records = [
                Occurrence(
                    ddr_id=occ["ddr_id"],
                    ddr_date_id=occ["ddr_date_id"],
                    type=occ["type"],
                    well_name=occ.get("well_name"),
                    surface_location=occ.get("surface_location"),
                    section=occ.get("section"),
                    mmd=occ.get("mmd"),
                    density=occ.get("density"),
                    notes=occ.get("notes"),
                    date=occ.get("date"),
                    is_exported=False,
                    created_at=now,
                    updated_at=now,
                )
                for occ in occurrences
            ]
            self.async_session.add_all(records)
        await self.async_session.commit()

    async def bulk_create_occurrences(self, occurrences: list[dict]) -> None:
        if not occurrences:
            return
        now = int(time.time())
        records = [
            Occurrence(
                ddr_id=occ["ddr_id"],
                ddr_date_id=occ["ddr_date_id"],
                type=occ["type"],
                well_name=occ.get("well_name"),
                surface_location=occ.get("surface_location"),
                section=occ.get("section"),
                mmd=occ.get("mmd"),
                density=occ.get("density"),
                notes=occ.get("notes"),
                date=occ.get("date"),
                is_exported=False,
                created_at=now,
                updated_at=now,
            )
            for occ in occurrences
        ]
        self.async_session.add_all(records)
        await self.async_session.commit()

    async def get_by_ddr_id_filtered(
        self,
        ddr_id: str,
        type_filter: str | None = None,
        section_filter: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[Occurrence]:
        stmt = (
            sqlalchemy.select(Occurrence)
            .where(Occurrence.ddr_id == ddr_id)
            .order_by(Occurrence.date.asc(), Occurrence.created_at.asc())
            .limit(limit)
            .offset(offset)
        )
        if type_filter is not None:
            stmt = stmt.where(Occurrence.type == type_filter)
        if section_filter is not None:
            stmt = stmt.where(Occurrence.section == section_filter)
        if date_from is not None:
            stmt = stmt.where(Occurrence.date >= date_from)
        if date_to is not None:
            stmt = stmt.where(Occurrence.date <= date_to)
        result = await self.async_session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_ddr_id(self, ddr_id: str, limit: int = 100, offset: int = 0) -> list[Occurrence]:
        stmt = sqlalchemy.select(Occurrence).where(Occurrence.ddr_id == ddr_id).limit(limit).offset(offset)
        result = await self.async_session.execute(stmt)
        return list(result.scalars().all())
