import time
import typing
from dataclasses import dataclass
from decimal import Decimal

import sqlalchemy

from src.models.db.ddr import DDR, DDRDate, PipelineRun, ProcessingQueue
from src.models.schemas.ddr import DDRDateStatus, DDRStatus
from src.repository.crud.base import BaseCRUDRepository
from src.utilities.exceptions import EntityDoesNotExist


@dataclass(frozen=True)
class PipelineCostAggregate:
    total_cost_usd: Decimal
    total_runs: int


class DDRCRUDRepository(BaseCRUDRepository[DDR]):
    model = DDR

    async def read_ddr_by_id(self, ddr_id: str) -> DDR:
        ddr = await self.read_by_id(ddr_id)
        if ddr is None:
            raise EntityDoesNotExist(f"DDR with id `{ddr_id}` does not exist!")
        return ddr

    async def read_ddrs_by_status(self, status: str) -> typing.Sequence[DDR]:
        stmt = sqlalchemy.select(DDR).where(DDR.status == DDRStatus.validate(status))
        query = await self.async_session.execute(statement=stmt)
        return query.scalars().all()

    async def update_status(self, ddr: DDR, status: str, commit: bool = True) -> DDR:
        ddr.status = DDRStatus.validate(status)
        ddr.updated_at = int(time.time())
        self.async_session.add(ddr)
        if commit:
            await self.async_session.commit()
            await self.async_session.refresh(ddr)
        else:
            await self.async_session.flush()
        return ddr

    async def read_all_descending(self) -> typing.Sequence[DDR]:
        stmt = sqlalchemy.select(DDR).order_by(DDR.created_at.desc())
        query = await self.async_session.execute(statement=stmt)
        return query.scalars().all()

    async def update_well_metadata(
        self,
        ddr: DDR,
        well_name: str | None,
        surface_location: str | None,
        commit: bool = True,
    ) -> DDR:
        return await self.update(
            ddr,
            {"well_name": well_name, "surface_location": surface_location, "updated_at": int(time.time())},
            commit=commit,
        )

    async def finalize_status_from_dates(self, ddr: DDR, date_statuses: typing.Iterable[str]) -> DDR:
        statuses = list(date_statuses)
        if not statuses:
            final = DDRStatus.FAILED
        elif any(status == DDRDateStatus.SUCCESS for status in statuses):
            final = DDRStatus.COMPLETE
        else:
            final = DDRStatus.FAILED
        return await self.update(ddr, {"status": final, "updated_at": int(time.time())})

    async def create_queued_with_queue(
        self,
        ddr_id: str,
        file_path: str,
        processing_queue_repository: "ProcessingQueueCRUDRepository",
        operator: str | None = None,
        area: str | None = None,
    ) -> DDR:
        now = int(time.time())
        position = await processing_queue_repository.next_position()
        ddr = DDR(
            id=ddr_id,
            file_path=file_path,
            status=DDRStatus.QUEUED,
            operator=operator,
            area=area,
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

    async def read_date_for_update(self, ddr_id: str, date: str) -> DDRDate | None:
        stmt = (
            sqlalchemy.select(DDRDate)
            .where(DDRDate.ddr_id == ddr_id, DDRDate.date == date)
            .with_for_update()
        )
        result = await self.async_session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_status(self, ddr_date: DDRDate, status: str) -> DDRDate:
        return await self.update(ddr_date, {"status": DDRDateStatus.validate(status), "updated_at": int(time.time())})

    async def bulk_create_queued(
        self,
        ddr_id: str,
        dates: typing.Iterable[str],
        commit: bool = True,
    ) -> typing.Sequence[DDRDate]:
        now = int(time.time())
        requested_dates = list(dict.fromkeys(dates))
        existing_rows = await self.read_dates_by_ddr_id(ddr_id)
        existing_dates = {row.date for row in existing_rows}
        records = [
            DDRDate(
                ddr_id=ddr_id,
                date=date,
                status=DDRDateStatus.validate(DDRDateStatus.QUEUED),
                created_at=now,
                updated_at=now,
            )
            for date in requested_dates
            if date not in existing_dates
        ]
        for record in records:
            self.async_session.add(record)
        if commit:
            await self.async_session.commit()
            for record in records:
                await self.async_session.refresh(record)
        else:
            await self.async_session.flush()
        return [*existing_rows, *records]

    async def bulk_update_source_page_numbers(
        self,
        ddr_id: str,
        date_page_numbers: dict[str, list[int]],
        commit: bool = True,
    ) -> typing.Sequence[DDRDate]:
        rows = await self.read_dates_by_ddr_id(ddr_id)
        for row in rows:
            if row.date in date_page_numbers:
                row.source_page_numbers = date_page_numbers[row.date]
                row.updated_at = int(time.time())
                self.async_session.add(row)
        if commit:
            await self.async_session.commit()
            for row in rows:
                await self.async_session.refresh(row)
        else:
            await self.async_session.flush()
        return rows

    async def mark_success(
        self,
        ddr_date: DDRDate,
        raw_response: dict,
        final_json: dict,
        commit: bool = True,
    ) -> DDRDate:
        return await self.update(
            ddr_date,
            {
                "status": DDRDateStatus.SUCCESS,
                "raw_response": raw_response,
                "final_json": final_json,
                "error_log": None,
                "updated_at": int(time.time()),
            },
            commit=commit,
        )

    async def mark_failed(
        self,
        ddr_date: DDRDate,
        error_log: dict,
        raw_response: dict | None = None,
        commit: bool = True,
    ) -> DDRDate:
        return await self.update(
            ddr_date,
            {
                "status": DDRDateStatus.FAILED,
                "raw_response": raw_response,
                "final_json": None,
                "error_log": error_log,
                "updated_at": int(time.time()),
            },
            commit=commit,
        )

    async def mark_warning(
        self,
        ddr_date: DDRDate,
        error_log: dict,
        raw_response: dict | None = None,
        commit: bool = True,
    ) -> DDRDate:
        return await self.update(
            ddr_date,
            {
                "status": DDRDateStatus.WARNING,
                "raw_response": raw_response,
                "final_json": None,
                "error_log": error_log,
                "updated_at": int(time.time()),
            },
            commit=commit,
        )

    async def mark_failed_preserve(
        self,
        ddr_date: DDRDate,
        error_log: dict,
        raw_response: dict | None = None,
        commit: bool = True,
    ) -> DDRDate:
        return await self.update(
            ddr_date,
            {
                "status": DDRDateStatus.FAILED,
                "raw_response": raw_response,
                "error_log": error_log,
                "updated_at": int(time.time()),
            },
            commit=commit,
        )

    async def mark_warning_preserve(
        self,
        ddr_date: DDRDate,
        error_log: dict,
        raw_response: dict | None = None,
        commit: bool = True,
    ) -> DDRDate:
        return await self.update(
            ddr_date,
            {
                "status": DDRDateStatus.WARNING,
                "raw_response": raw_response,
                "error_log": error_log,
                "updated_at": int(time.time()),
            },
            commit=commit,
        )

    async def delete_by_ddr_id_and_dates(self, ddr_id: str, dates: list[str]) -> None:
        if not dates:
            return
        stmt = sqlalchemy.delete(DDRDate).where(
            DDRDate.ddr_id == ddr_id,
            DDRDate.date.in_(dates),
        )
        await self.async_session.execute(stmt)
        await self.async_session.commit()

    async def create_failed_boundary(
        self,
        ddr_id: str,
        date: str,
        reason: str,
        raw_page_content: str,
        commit: bool = True,
    ) -> DDRDate:
        now = int(time.time())
        record = DDRDate(
            ddr_id=ddr_id,
            date=date,
            status=DDRDateStatus.validate(DDRDateStatus.FAILED),
            error_log={"reason": reason, "raw_page_content": raw_page_content},
            created_at=now,
            updated_at=now,
        )
        self.async_session.add(record)
        if commit:
            await self.async_session.commit()
            await self.async_session.refresh(record)
        else:
            await self.async_session.flush()
        return record


class ProcessingQueueCRUDRepository(BaseCRUDRepository[ProcessingQueue]):
    model = ProcessingQueue
    queue_position_lock_id = 202605070022

    async def next_position(self) -> int:
        await self.async_session.execute(
            sqlalchemy.text("SELECT pg_advisory_xact_lock(:lock_id)"),
            {"lock_id": self.queue_position_lock_id},
        )
        stmt = sqlalchemy.select(sqlalchemy.func.coalesce(sqlalchemy.func.max(ProcessingQueue.position), 0) + 1)
        query = await self.async_session.execute(statement=stmt)
        return int(query.scalar_one())

    async def read_active_ordered(self) -> typing.Sequence[ProcessingQueue]:
        stmt = (
            sqlalchemy.select(ProcessingQueue)
            .join(DDR, DDR.id == ProcessingQueue.ddr_id)
            .where(DDR.status.in_((DDRStatus.QUEUED, DDRStatus.PROCESSING)))
            .order_by(ProcessingQueue.position.asc(), ProcessingQueue.created_at.asc())
        )
        query = await self.async_session.execute(statement=stmt)
        return query.scalars().all()

    async def delete_by_ddr_id(self, ddr_id: str) -> None:
        stmt = sqlalchemy.delete(ProcessingQueue).where(ProcessingQueue.ddr_id == ddr_id)
        await self.async_session.execute(stmt)
        await self.async_session.commit()


class PipelineRunCRUDRepository(BaseCRUDRepository[PipelineRun]):
    model = PipelineRun

    async def create_pipeline_run(
        self,
        ddr_date_id: str,
        gemini_input_tokens: int | None = None,
        gemini_output_tokens: int | None = None,
        cost_usd: Decimal | None = None,
        commit: bool = True,
    ) -> PipelineRun:
        return await self.create(
            {
                "ddr_date_id": ddr_date_id,
                "gemini_input_tokens": gemini_input_tokens,
                "gemini_output_tokens": gemini_output_tokens,
                "cost_usd": cost_usd,
                "created_at": int(time.time()),
            },
            commit=commit,
        )

    async def aggregate_all_time_cost(self) -> PipelineCostAggregate:
        stmt = sqlalchemy.select(
            sqlalchemy.func.coalesce(sqlalchemy.func.sum(PipelineRun.cost_usd), Decimal("0.000000")),
            sqlalchemy.func.count(PipelineRun.id),
        )
        result = await self.async_session.execute(stmt)
        total_cost_usd, total_runs = result.one()
        return PipelineCostAggregate(
            total_cost_usd=Decimal(total_cost_usd or Decimal("0.000000")),
            total_runs=int(total_runs or 0),
        )
