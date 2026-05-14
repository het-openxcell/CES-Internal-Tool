import re
import time
from typing import Any

import sqlalchemy

from src.models.db.ddr import DDR, DDRDate
from src.models.db.occurrence import Occurrence
from src.services.occurrence.classify import classify_section
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
        page_number: int | None = None,
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
                "page_number": page_number,
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
                    page_number=occ.get("page_number"),
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
                page_number=occ.get("page_number"),
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

    async def search_history(
        self,
        type_filters: list[str] | None = None,
        section_filters: list[str] | None = None,
        operator_filters: list[str] | None = None,
        depth_from: float | None = None,
        depth_to: float | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[dict]:
        stmt = (
            sqlalchemy.select(
                Occurrence.id,
                Occurrence.ddr_id,
                Occurrence.ddr_date_id,
                Occurrence.well_name,
                Occurrence.surface_location,
                Occurrence.type,
                Occurrence.section,
                Occurrence.mmd,
                Occurrence.density,
                Occurrence.notes,
                Occurrence.date,
                Occurrence.page_number,
                Occurrence.is_exported,
                DDR.operator.label("operator"),
                DDR.area.label("area"),
                DDRDate.final_json.label("final_json"),
            )
            .join(DDR, DDR.id == Occurrence.ddr_id)
            .join(DDRDate, DDRDate.id == Occurrence.ddr_date_id)
            .order_by(Occurrence.date.desc().nullslast(), Occurrence.mmd.asc().nullslast(), Occurrence.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if type_filters:
            stmt = stmt.where(Occurrence.type.in_(type_filters))
        if section_filters:
            stmt = stmt.where(Occurrence.section.in_(section_filters))
        if operator_filters:
            stmt = stmt.where(DDR.operator.in_(operator_filters))
        if depth_from is not None:
            stmt = stmt.where(Occurrence.mmd >= depth_from)
        if depth_to is not None:
            stmt = stmt.where(Occurrence.mmd <= depth_to)
        if date_from is not None:
            stmt = stmt.where(Occurrence.date >= date_from)
        if date_to is not None:
            stmt = stmt.where(Occurrence.date <= date_to)
        result = await self.async_session.execute(stmt)
        rows = []
        for row in result.mappings().all():
            data = dict(row)
            final_json = data.pop("final_json", None)
            data.update(self._history_metadata(data, final_json))
            rows.append(data)
        return rows

    def _history_metadata(self, occurrence: dict[str, Any], final_json: dict[str, Any] | None) -> dict[str, Any]:
        time_log = self._matching_time_log(occurrence.get("notes"), final_json)
        from_mmd, to_mmd = self._depth_range(occurrence, time_log)
        section = occurrence.get("section")
        if section is None:
            section_depth = to_mmd if to_mmd is not None else from_mmd
            section = classify_section(section_depth)
        return {
            "start_time": time_log.get("start_time") if time_log else None,
            "end_time": time_log.get("end_time") if time_log else None,
            "from_mmd": from_mmd,
            "to_mmd": to_mmd,
            "section": section,
        }

    def _matching_time_log(self, notes: str | None, final_json: dict[str, Any] | None) -> dict[str, Any] | None:
        if not notes or not isinstance(final_json, dict):
            return None
        time_logs = final_json.get("time_logs")
        if not isinstance(time_logs, list):
            return None
        normalized_notes = self._normalize_text(notes)
        for time_log in time_logs:
            if not isinstance(time_log, dict):
                continue
            fields = [time_log.get("comment"), time_log.get("activity")]
            text = " ".join(str(value) for value in fields if value)
            normalized_text = self._normalize_text(text)
            if normalized_notes == normalized_text or normalized_notes in normalized_text or normalized_text in normalized_notes:
                return time_log
        return None

    def _depth_range(self, occurrence: dict[str, Any], time_log: dict[str, Any] | None) -> tuple[float | None, float | None]:
        mmd = self._to_float(occurrence.get("mmd"))
        if mmd is not None:
            return mmd, mmd
        depth_md = self._to_float(time_log.get("depth_md")) if time_log else None
        if depth_md is not None:
            return depth_md, depth_md
        text_parts = [occurrence.get("notes")]
        if time_log:
            text_parts.extend([time_log.get("activity"), time_log.get("comment")])
        text = " ".join(str(value) for value in text_parts if value)
        return self._parse_depth_range(text)

    def _parse_depth_range(self, text: str) -> tuple[float | None, float | None]:
        range_match = re.search(r"\b(\d{2,5}(?:\.\d+)?)\s*m?\s*(?:-|–|to)\s*(\d{2,5}(?:\.\d+)?)\s*m\b", text, re.IGNORECASE)
        if range_match:
            first = self._to_float(range_match.group(1))
            second = self._to_float(range_match.group(2))
            if first is not None and second is not None:
                return min(first, second), max(first, second)
        single_matches = re.findall(r"\b(?:to|at|depth|mmd|from)\s*(\d{2,5}(?:\.\d+)?)\s*m\b", text, re.IGNORECASE)
        if single_matches:
            depth = self._to_float(single_matches[-1])
            return depth, depth
        return None, None

    def _normalize_text(self, value: str) -> str:
        return " ".join(value.lower().split())

    def _to_float(self, value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
