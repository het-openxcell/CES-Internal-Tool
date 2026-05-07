import time
import typing
from decimal import Decimal

import sqlalchemy

from src.models.db.ddr import DDR, DDRDate, PipelineRun, ProcessingQueue
from src.models.schemas.ddr import DDRDateStatus, DDRStatus
from src.repository.crud.base import BaseCRUDRepository
from src.utilities.exceptions import EntityDoesNotExist


class DDRCRUDRepository(BaseCRUDRepository[DDR]):
    model = DDR

    async def create_ddr(self, file_path: str, well_name: str | None = None, status: str = DDRStatus.QUEUED) -> DDR:
        now = int(time.time())
        return await self.create(
            {
                "file_path": file_path,
                "well_name": well_name,
                "status": DDRStatus.validate(status),
                "created_at": now,
                "updated_at": now,
            }
        )

    async def read_ddr_by_id(self, ddr_id: str) -> DDR:
        ddr = await self.read_by_id(ddr_id)
        if ddr is None:
            raise EntityDoesNotExist(f"DDR with id `{ddr_id}` does not exist!")
        return ddr

    async def read_ddrs_by_status(self, status: str) -> typing.Sequence[DDR]:
        stmt = sqlalchemy.select(DDR).where(DDR.status == DDRStatus.validate(status))
        query = await self.async_session.execute(statement=stmt)
        return query.scalars().all()

    async def update_status(self, ddr: DDR, status: str) -> DDR:
        return await self.update(ddr, {"status": DDRStatus.validate(status), "updated_at": int(time.time())})

    async def read_all_descending(self) -> typing.Sequence[DDR]:
        stmt = sqlalchemy.select(DDR).order_by(DDR.created_at.desc())
        query = await self.async_session.execute(statement=stmt)
        return query.scalars().all()

    async def create_queued_with_queue(
        self,
        ddr_id: str,
        file_path: str,
        processing_queue_repository: "ProcessingQueueCRUDRepository",
    ) -> DDR:
        now = int(time.time())
        position = await processing_queue_repository.next_position()
        ddr = DDR(
            id=ddr_id,
            file_path=file_path,
            status=DDRStatus.QUEUED,
            created_at=now,
            updated_at=now,
        )
        queue_entry = ProcessingQueue(ddr_id=ddr_id, position=position, created_at=now)
        self.async_session.add(ddr)
        self.async_session.add(queue_entry)
        await self.async_session.commit()
        await self.async_session.refresh(ddr)
        return ddr


class DDRDateCRUDRepository(BaseCRUDRepository[DDRDate]):
    model = DDRDate

    async def create_ddr_date(self, ddr_id: str, date: str, status: str = DDRDateStatus.QUEUED) -> DDRDate:
        now = int(time.time())
        return await self.create(
            {
                "ddr_id": ddr_id,
                "date": date,
                "status": DDRDateStatus.validate(status),
                "created_at": now,
                "updated_at": now,
            }
        )

    async def read_dates_by_ddr_id(self, ddr_id: str) -> typing.Sequence[DDRDate]:
        stmt = sqlalchemy.select(DDRDate).where(DDRDate.ddr_id == ddr_id).order_by(DDRDate.date.asc())
        query = await self.async_session.execute(statement=stmt)
        return query.scalars().all()

    async def update_status(self, ddr_date: DDRDate, status: str) -> DDRDate:
        return await self.update(ddr_date, {"status": DDRDateStatus.validate(status), "updated_at": int(time.time())})


class ProcessingQueueCRUDRepository(BaseCRUDRepository[ProcessingQueue]):
    model = ProcessingQueue
    queue_position_lock_id = 202605070022

    async def create_queue_entry(self, ddr_id: str, position: int) -> ProcessingQueue:
        return await self.create({"ddr_id": ddr_id, "position": position, "created_at": int(time.time())})

    async def next_position(self) -> int:
        await self.async_session.execute(
            sqlalchemy.text("SELECT pg_advisory_xact_lock(:lock_id)"),
            {"lock_id": self.queue_position_lock_id},
        )
        stmt = sqlalchemy.select(sqlalchemy.func.coalesce(sqlalchemy.func.max(ProcessingQueue.position), 0) + 1)
        query = await self.async_session.execute(statement=stmt)
        return int(query.scalar_one())

    async def read_queue_by_ddr_id(self, ddr_id: str) -> ProcessingQueue | None:
        stmt = sqlalchemy.select(ProcessingQueue).where(ProcessingQueue.ddr_id == ddr_id)
        query = await self.async_session.execute(statement=stmt)
        return query.scalar_one_or_none()


class PipelineRunCRUDRepository(BaseCRUDRepository[PipelineRun]):
    model = PipelineRun

    async def create_pipeline_run(
        self,
        ddr_date_id: str,
        gemini_input_tokens: int | None = None,
        gemini_output_tokens: int | None = None,
        cost_usd: Decimal | None = None,
    ) -> PipelineRun:
        return await self.create(
            {
                "ddr_date_id": ddr_date_id,
                "gemini_input_tokens": gemini_input_tokens,
                "gemini_output_tokens": gemini_output_tokens,
                "cost_usd": cost_usd,
                "created_at": int(time.time()),
            }
        )
