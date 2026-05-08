import asyncio
from collections import defaultdict
from typing import Any, Awaitable, Callable

from pydantic import BaseModel

from src.models.schemas.ddr import (
    DDRDateCompleteEvent,
    DDRDateFailedEvent,
    DDRDateStatus,
    DDRProcessingCompleteEvent,
    DDRStatus,
)


class ProcessingStatusEvent:
    def __init__(self, name: str, payload: BaseModel) -> None:
        self.name = name
        self.payload = payload

    def frame(self) -> str:
        return f"event: {self.name}\ndata: {self.payload.model_dump_json()}\n\n"


class ProcessingStatusStreamService:
    date_complete_event = "date_complete"
    date_failed_event = "date_failed"
    processing_complete_event = "processing_complete"

    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue[ProcessingStatusEvent]]] = defaultdict(set)
        self._lock = asyncio.Lock()

    def stream(
        self,
        ddr_id: str,
        request: Any,
        send_open_frame: bool = False,
        initial_events: list[ProcessingStatusEvent] | None = None,
        initial_events_factory: Callable[[], Awaitable[list[ProcessingStatusEvent]]] | None = None,
    ) -> Any:
        queue: asyncio.Queue[ProcessingStatusEvent] = asyncio.Queue()
        self._subscribers[ddr_id].add(queue)

        async def generator() -> Any:
            try:
                if send_open_frame:
                    yield ": connected\n\n"
                snapshot_events = (
                    await initial_events_factory()
                    if initial_events_factory is not None
                    else initial_events or []
                )
                for event in snapshot_events:
                    yield event.frame()
                    if event.name == self.processing_complete_event:
                        return
                while True:
                    if await request.is_disconnected():
                        break
                    try:
                        event = await asyncio.wait_for(queue.get(), timeout=1)
                    except TimeoutError:
                        continue
                    yield event.frame()
                    if event.name == self.processing_complete_event:
                        break
            finally:
                await self.unsubscribe(ddr_id, queue)

        return generator()

    def snapshot_events(self, ddr: Any, rows: list[Any]) -> list[ProcessingStatusEvent]:
        events = []
        for row in rows:
            if row.status in (DDRDateStatus.SUCCESS, DDRDateStatus.WARNING):
                events.append(
                    ProcessingStatusEvent(
                        self.date_complete_event,
                        DDRDateCompleteEvent(date=row.date, status=row.status, occurrences_count=0),
                    )
                )
            if row.status == DDRDateStatus.FAILED:
                events.append(
                    ProcessingStatusEvent(
                        self.date_failed_event,
                        DDRDateFailedEvent(
                            date=row.date,
                            error=self._error_message(row),
                            raw_response_id=self._raw_response_id(row),
                        ),
                    )
                )
        if ddr.status in (DDRStatus.COMPLETE, DDRStatus.FAILED):
            events.append(
                ProcessingStatusEvent(
                    self.processing_complete_event,
                    DDRProcessingCompleteEvent(
                        total_dates=len(rows),
                        failed_dates=sum(1 for row in rows if row.status == DDRDateStatus.FAILED),
                        warning_dates=sum(1 for row in rows if row.status == DDRDateStatus.WARNING),
                        total_occurrences=0,
                    ),
                )
            )
        return events

    async def unsubscribe(self, ddr_id: str, queue: asyncio.Queue[ProcessingStatusEvent]) -> None:
        async with self._lock:
            subscribers = self._subscribers.get(ddr_id)
            if subscribers is None:
                return
            subscribers.discard(queue)
            if not subscribers:
                self._subscribers.pop(ddr_id, None)

    async def publish(self, ddr_id: str, event_name: str, payload: BaseModel) -> None:
        event = ProcessingStatusEvent(event_name, payload)
        for queue in list(self._subscribers.get(ddr_id, set())):
            await queue.put(event)

    async def publish_date_complete(
        self,
        ddr_id: str,
        date: str,
        occurrences_count: int = 0,
        status: str = DDRDateStatus.SUCCESS,
    ) -> None:
        await self.publish(
            ddr_id,
            self.date_complete_event,
            DDRDateCompleteEvent(date=date, status=status, occurrences_count=occurrences_count),
        )

    async def publish_date_failed(self, ddr_id: str, date: str, error: str, raw_response_id: str) -> None:
        await self.publish(
            ddr_id,
            self.date_failed_event,
            DDRDateFailedEvent(date=date, error=error, raw_response_id=raw_response_id),
        )

    async def publish_processing_complete(
        self,
        ddr_id: str,
        total_dates: int,
        failed_dates: int,
        warning_dates: int,
        total_occurrences: int = 0,
    ) -> None:
        await self.publish(
            ddr_id,
            self.processing_complete_event,
            DDRProcessingCompleteEvent(
                total_dates=total_dates,
                failed_dates=failed_dates,
                warning_dates=warning_dates,
                total_occurrences=total_occurrences,
            ),
        )

    def _error_message(self, row: Any) -> str:
        error_log = getattr(row, "error_log", None)
        if isinstance(error_log, dict):
            for key in ("detail", "reason", "error"):
                if error_log.get(key):
                    return str(error_log[key])
            if error_log.get("errors"):
                return str(error_log["errors"])
            if error_log.get("code"):
                return str(error_log["code"])
        return "processing_failed"

    def _raw_response_id(self, row: Any) -> str:
        raw_response = getattr(row, "raw_response", None)
        if isinstance(raw_response, dict):
            for key in ("id", "raw_response_id", "response_id"):
                if raw_response.get(key):
                    return str(raw_response[key])
        return str(row.id)
