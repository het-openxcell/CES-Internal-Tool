import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest

import src.services.pipeline_service as pipeline_service_module
from src.config.manager import settings
from src.models.schemas.ddr import DDRDateStatus, DDRStatus
from src.services.pipeline.extract import ExtractionResult
from src.services.pipeline.validate import DDRExtractionValidator
from src.services.pipeline_service import PreSplitPipelineService

FIXTURE_JSON = (Path(__file__).parent / "fixtures" / "expected_timelogs.json").read_text()


class FakeDDRDateRow:
    def __init__(self, date: str, ddr_id: str) -> None:
        self.id = f"{ddr_id}-{date}"
        self.ddr_id = ddr_id
        self.date = date
        self.status = DDRDateStatus.QUEUED
        self.raw_response = None
        self.final_json = None
        self.error_log = None
        self.source_page_numbers = None
        self.updated_at = 0


class FakeDDRDateRepository:
    def __init__(self, rows: list[FakeDDRDateRow]) -> None:
        self.async_session = None
        self._rows = rows
        self.failure_calls: list[dict] = []

    async def read_dates_by_ddr_id(self, ddr_id):
        return [row for row in self._rows if row.ddr_id == ddr_id]

    async def update_status(self, row, status):
        row.status = status
        return row

    async def mark_success(self, row, raw_response, final_json, commit=True):
        row.status = DDRDateStatus.SUCCESS
        row.raw_response = raw_response
        row.final_json = final_json
        row.error_log = None
        return row

    async def mark_failed(self, row, error_log, raw_response=None):
        row.status = DDRDateStatus.FAILED
        row.raw_response = raw_response
        row.final_json = None
        row.error_log = error_log
        self.failure_calls.append({"row": row, "error_log": error_log})
        return row

    async def mark_warning(self, row, error_log, raw_response=None):
        row.status = DDRDateStatus.WARNING
        row.error_log = error_log
        return row

    async def bulk_create_queued(self, ddr_id, dates, commit=True):
        return [row for row in self._rows if row.ddr_id == ddr_id]

    async def bulk_update_source_page_numbers(self, ddr_id, date_page_numbers, commit=True):
        return self._rows

    async def create_failed_boundary(self, **kwargs):
        return None


class FakeDDR:
    def __init__(self, ddr_id: str) -> None:
        self.id = ddr_id
        self.file_path = "/tmp/ddr.pdf"
        self.status = DDRStatus.QUEUED
        self.updated_at = 0


class FakeDDRRepository:
    def __init__(self, ddr: FakeDDR) -> None:
        self.async_session = None
        self._ddr = ddr

    async def read_ddr_by_id(self, ddr_id):
        return self._ddr

    async def read_status(self, ddr_id):
        return self._ddr.status

    async def update_status(self, ddr, status, commit=True):
        ddr.status = status
        return ddr

    async def finalize_status_from_dates(self, ddr, statuses):
        s = list(statuses)
        ddr.status = DDRStatus.COMPLETE if any(x == DDRDateStatus.SUCCESS for x in s) else DDRStatus.FAILED
        return ddr

    async def update_well_metadata(self, ddr, well_name, surface_location, commit=True):
        return ddr


class FakeStorageService:
    async def upload_chunk(self, ddr_id: str, date: str, data: bytes) -> str:
        return f"ces/ddrs/{ddr_id}/chunks/{date}.pdf"

    async def download_chunk(self, ddr_id: str, date: str) -> bytes:
        return b"%PDF-1.7"

    async def delete_ddr(self, ddr_id: str) -> None:
        return None


class FakeCostService:
    async def record_extraction_run(self, *, ddr_date_id, input_tokens, output_tokens, commit=True):
        return SimpleNamespace(id="run-1")


class FakeEmbeddingService:
    async def embed_successful_date(self, row):
        return None


class NoopStatusStream:
    async def publish_date_started(self, ddr_id, date):
        return None

    async def publish_date_complete(self, *args, **kwargs):
        return None

    async def publish_date_failed(self, *args, **kwargs):
        return None

    async def publish_processing_complete(self, *args, **kwargs):
        return None


class ConcurrencyTrackingExtractor:
    """Records how many extract() calls are in flight at once, across ALL instances/DDRs sharing it."""

    def __init__(self) -> None:
        self.active = 0
        self.max_active = 0
        self.lock = asyncio.Lock()

    async def extract(self, *, date, pdf_bytes, original_page_numbers=None):
        async with self.lock:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        try:
            await asyncio.sleep(0.05)
            return ExtractionResult(text=FIXTURE_JSON, input_tokens=1, output_tokens=1)
        finally:
            async with self.lock:
                self.active -= 1


def make_service(ddr_id: str, dates: list[str], extractor, *, max_concurrent=None):
    rows = [FakeDDRDateRow(date, ddr_id) for date in dates]
    date_repo = FakeDDRDateRepository(rows)
    ddr = FakeDDR(ddr_id)
    ddr_repo = FakeDDRRepository(ddr)

    async def loader(_):
        return b"%PDF-1.7"

    async def fake_split(_):
        return SimpleNamespace(
            has_boundaries=True,
            date_chunks={date: date.encode() for date in dates},
            raw_text_preview="",
        )

    kwargs = dict(
        ddr_repository=ddr_repo,
        ddr_date_repository=date_repo,
        pre_splitter=SimpleNamespace(split_async=fake_split),
        pdf_loader=loader,
        extractor=extractor,
        validator=DDRExtractionValidator(),
        extract_after_split=True,
        status_stream_service=NoopStatusStream(),
        storage_service=FakeStorageService(),
        cost_service=FakeCostService(),
        embedding_service=FakeEmbeddingService(),
    )
    if max_concurrent is not None:
        kwargs["max_concurrent"] = max_concurrent
    return PreSplitPipelineService(**kwargs), rows, ddr


async def _run_both(service_a, service_b):
    await asyncio.gather(
        service_a.run(service_a.ddr_repository._ddr.id),
        service_b.run(service_b.ddr_repository._ddr.id),
    )


@pytest.fixture(autouse=True)
def reset_shared_semaphore(monkeypatch):
    """Each test gets a fresh global semaphore so tests don't leak state into each other."""
    monkeypatch.setattr(pipeline_service_module, "_shared_extraction_semaphore", None)
    yield
    monkeypatch.setattr(pipeline_service_module, "_shared_extraction_semaphore", None)


def test_default_instances_share_one_global_semaphore_across_ddrs(monkeypatch):
    """
    Two DDRs processed at the same time, neither passing max_concurrent (the real
    production path — see get_pipeline_service / DDRProcessingTask), must together
    never exceed the GLOBAL limit. Before the fix, each DDR got its own private
    semaphore, so two DDRs could each run up to the limit simultaneously (2x over).
    """
    monkeypatch.setattr(settings, "GEMINI_EXTRACTION_MAX_CONCURRENT", 1)

    shared_extractor = ConcurrencyTrackingExtractor()
    service_a, rows_a, ddr_a = make_service("ddr-a", ["20240101", "20240102"], shared_extractor)
    service_b, rows_b, ddr_b = make_service("ddr-b", ["20240201", "20240202"], shared_extractor)

    asyncio.run(_run_both(service_a, service_b))

    assert shared_extractor.max_active <= 1, (
        f"expected global cap of 1 concurrent extraction across both DDRs, "
        f"observed {shared_extractor.max_active} — semaphore is not actually shared"
    )
    assert all(row.status == DDRDateStatus.SUCCESS for row in rows_a + rows_b)
    assert ddr_a.status == DDRStatus.COMPLETE
    assert ddr_b.status == DDRStatus.COMPLETE


def test_explicit_max_concurrent_still_gets_its_own_isolated_semaphore(monkeypatch):
    """
    Existing tests (and any future caller) that explicitly pass max_concurrent must
    keep getting a private semaphore sized exactly as requested, unaffected by the
    global default and unaffected by other concurrently-running instances.
    """
    monkeypatch.setattr(settings, "GEMINI_EXTRACTION_MAX_CONCURRENT", 1)

    extractor_a = ConcurrencyTrackingExtractor()
    extractor_b = ConcurrencyTrackingExtractor()
    service_a, rows_a, _ = make_service("ddr-a", ["20240101", "20240102"], extractor_a, max_concurrent=2)
    service_b, rows_b, _ = make_service("ddr-b", ["20240201", "20240202"], extractor_b, max_concurrent=2)

    asyncio.run(_run_both(service_a, service_b))

    assert extractor_a.max_active <= 2
    assert extractor_b.max_active <= 2
    assert all(row.status == DDRDateStatus.SUCCESS for row in rows_a + rows_b)


def test_unhandled_exception_before_any_try_block_still_marks_date_failed_not_stuck_queued():
    """
    Reproduces the "stalled forever" bug: an exception thrown before extraction's own
    try/except (e.g. a transient failure publishing the started-event, which can happen
    under DB/connection contention) used to propagate out of _process_one_date entirely,
    get swallowed by asyncio.gather(return_exceptions=True), and leave the date row stuck
    at QUEUED forever with the DDR parked in PROCESSING. It must now always end up FAILED.
    """

    class RaisingStatusStream(NoopStatusStream):
        async def publish_date_started(self, ddr_id, date):
            raise RuntimeError("simulated transient failure publishing date_started")

    extractor = ConcurrencyTrackingExtractor()
    service, rows, ddr = make_service("ddr-1", ["20240101"], extractor, max_concurrent=1)
    service.status_stream_service = RaisingStatusStream()

    asyncio.run(service.run("ddr-1"))

    assert rows[0].status == DDRDateStatus.FAILED, "date must never be left stuck at QUEUED"
    assert rows[0].error_log["code"] == "UNRECOVERABLE"
    assert ddr.status in (DDRStatus.COMPLETE, DDRStatus.FAILED), "DDR must reach a terminal state, not stay PROCESSING"


def test_process_one_date_wrapper_survives_when_failure_marking_itself_also_throws():
    """
    Even if writing the failure status back to the DB also fails (total DB outage),
    _process_one_date must not raise — it must degrade to returning FAILED so the
    gather() loop and caller code keep working, instead of crashing the whole batch.
    """

    class RaisingStatusStream(NoopStatusStream):
        async def publish_date_started(self, ddr_id, date):
            raise RuntimeError("simulated transient failure")

    class DoubleFailingDateRepository(FakeDDRDateRepository):
        async def mark_failed(self, row, error_log, raw_response=None):
            raise RuntimeError("db is down, cannot even mark failed")

    extractor = ConcurrencyTrackingExtractor()
    service, rows, _ = make_service("ddr-1", ["20240101"], extractor, max_concurrent=1)
    service.status_stream_service = RaisingStatusStream()
    service.ddr_date_repository = DoubleFailingDateRepository(rows)

    row = rows[0]
    result = asyncio.run(
        service._process_one_date(
            extractor=extractor,
            row=row,
            date="20240101",
            chunk_bytes=b"x",
        )
    )
    assert result == DDRDateStatus.FAILED
