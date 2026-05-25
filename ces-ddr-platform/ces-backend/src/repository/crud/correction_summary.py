import sqlalchemy
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import selectinload

from src.models.db.correction_summary import CorrectionSummary
from src.repository.crud.base import BaseCRUDRepository

_MAX_LIMIT = 10000


class CorrectionSummaryCRUDRepository(BaseCRUDRepository[CorrectionSummary]):
    model = CorrectionSummary

    async def upsert_date_summary(
        self,
        ddr_id: str,
        ddr_date_id: str,
        summary: str,
        source_logs: list[dict],
        edit_details: list[dict],
        correction_count: int,
        updated_at: int,
        commit: bool = False,
    ) -> CorrectionSummary:
        stmt = (
            insert(self.model)
            .values(
                ddr_id=ddr_id,
                ddr_date_id=ddr_date_id,
                scope="date",
                summary=summary,
                source_logs=source_logs,
                edit_details=edit_details,
                correction_count=correction_count,
                updated_at=updated_at,
            )
            .on_conflict_do_update(
                constraint="uq_correction_summaries_date_scope",
                set_={
                    "summary": summary,
                    "source_logs": source_logs,
                    "edit_details": edit_details,
                    "correction_count": correction_count,
                    "updated_at": updated_at,
                },
                where=self.model.correction_count <= correction_count,
            )
            .returning(self.model)
        )
        result = await self.async_session.execute(stmt)
        row = result.scalar_one_or_none()
        if commit:
            await self.async_session.commit()
        if row is not None:
            return row
        existing = await self.get_by_ddr_date_id(ddr_date_id)
        if existing is None:
            raise RuntimeError("correction_summary_upsert_returned_no_row")
        return existing

    async def get_by_ddr_id(self, ddr_id: str, limit: int = 100, offset: int = 0) -> list[CorrectionSummary]:
        limit = min(limit, _MAX_LIMIT)
        stmt = (
            sqlalchemy.select(self.model)
            .options(selectinload(self.model.ddr_date))
            .where(self.model.ddr_id == ddr_id)
            .order_by(self.model.updated_at.desc(), self.model.id.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.async_session.execute(stmt)
        return list(result.scalars().all())

    async def get_recent(self, limit: int = 100) -> list[CorrectionSummary]:
        limit = min(limit, _MAX_LIMIT)
        stmt = (
            sqlalchemy.select(self.model)
            .options(selectinload(self.model.ddr_date))
            .order_by(self.model.updated_at.desc(), self.model.id.desc())
            .limit(limit)
        )
        result = await self.async_session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_ddr_date_id(self, ddr_date_id: str) -> CorrectionSummary | None:
        stmt = sqlalchemy.select(self.model).options(selectinload(self.model.ddr_date)).where(
            self.model.ddr_date_id == ddr_date_id,
            self.model.scope == "date",
        )
        result = await self.async_session.execute(stmt)
        return result.scalar_one_or_none()
