import sqlalchemy

from src.models.db.correction import Correction
from src.repository.crud.base import BaseCRUDRepository

_MAX_LIMIT = 500


class CorrectionCRUDRepository(BaseCRUDRepository[Correction]):
    model = Correction

    async def create_correction(
        self,
        occurrence_id: str,
        ddr_id: str,
        field_name: str,
        original_value: str,
        corrected_value: str,
        reason: str,
        user_id: str,
        commit: bool = True,
    ) -> Correction:
        return await self.create(
            {
                "occurrence_id": occurrence_id,
                "ddr_id": ddr_id,
                "field_name": field_name,
                "original_value": original_value,
                "corrected_value": corrected_value,
                "reason": reason,
                "user_id": user_id,
            },
            commit=commit,
        )

    async def get_by_ddr_id(self, ddr_id: str, limit: int = 100, offset: int = 0) -> list[Correction]:
        limit = min(limit, _MAX_LIMIT)
        stmt = (
            sqlalchemy.select(self.model)
            .where(self.model.ddr_id == ddr_id)
            .order_by(self.model.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.async_session.execute(stmt)
        return list(result.scalars().all())

    async def get_all(
        self,
        field_name: str | None = None,
        ddr_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Correction]:
        limit = min(limit, _MAX_LIMIT)
        stmt = sqlalchemy.select(self.model).order_by(self.model.created_at.desc())
        if field_name is not None:
            stmt = stmt.where(self.model.field_name == field_name)
        if ddr_id is not None:
            stmt = stmt.where(self.model.ddr_id == ddr_id)
        stmt = stmt.limit(limit).offset(offset)
        result = await self.async_session.execute(stmt)
        return list(result.scalars().all())

    async def get_recent(self, limit: int = 20) -> list[Correction]:
        limit = min(limit, _MAX_LIMIT)
        stmt = sqlalchemy.select(self.model).order_by(self.model.created_at.desc()).limit(limit)
        result = await self.async_session.execute(stmt)
        return list(result.scalars().all())
