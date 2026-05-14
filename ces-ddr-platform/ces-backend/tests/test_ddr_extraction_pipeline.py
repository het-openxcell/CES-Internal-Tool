import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

from src.models.schemas.ddr import DDRDateStatus, DDRStatus
from src.services.pipeline.extract import (
    ExtractionError,
    ExtractionResult,
    GeminiDDRExtractor,
    RateLimitError,
)
from src.services.pipeline.validate import DDRExtractionValidator
from src.services.pipeline_service import PreSplitPipelineService

FIXTURE = Path(__file__).parent / "fixtures" / "expected_timelogs.json"
FIXTURE_JSON = FIXTURE.read_text()


class FakeGeminiClient:
    def __init__(self, responses: list):
        self._responses = list(responses)
        self.calls = []

    async def generate_content(self, *, model, pdf_bytes, prompt, response_schema):
        self.calls.append({"model": model, "pdf_bytes": pdf_bytes, "prompt": prompt})
        if not self._responses:
            raise AssertionError("no fake responses left")
        item = self._responses.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


class FakeDDRDateRow:
    def __init__(self, date: str, ddr_id: str = "ddr-1"):
        self.id = f"row-{date}"
        self.ddr_id = ddr_id
        self.date = date
        self.status = DDRDateStatus.QUEUED
        self.raw_response = None
        self.final_json = None
        self.error_log = None
        self.updated_at = 0


class FakeDDRDateRepository:
    def __init__(self, rows: list[FakeDDRDateRow]):
        self._rows = rows
        self.success_calls = []
        self.failure_calls = []
        self.warning_calls = []

    async def read_dates_by_ddr_id(self, ddr_id):
        return list(self._rows)

    async def read_date_for_update(self, ddr_id, date):
        return next((row for row in self._rows if row.ddr_id == ddr_id and row.date == date), None)

    async def update_status(self, row, status):
        row.status = status
        return row

    async def mark_success(self, row, raw_response, final_json, commit=True):
        row.status = DDRDateStatus.SUCCESS
        row.raw_response = raw_response
        row.final_json = final_json
        row.error_log = None
        self.success_calls.append({"row": row, "raw_response": raw_response, "final_json": final_json})
        return row

    async def mark_failed(self, row, error_log, raw_response=None):
        row.status = DDRDateStatus.FAILED
        row.raw_response = raw_response
        row.final_json = None
        row.error_log = error_log
        self.failure_calls.append({"row": row, "error_log": error_log, "raw_response": raw_response})
        return row

    async def mark_warning(self, row, error_log, raw_response=None):
        row.status = DDRDateStatus.WARNING
        row.raw_response = raw_response
        row.final_json = None
        row.error_log = error_log
        self.warning_calls.append({"row": row, "error_log": error_log, "raw_response": raw_response})
        return row

    async def bulk_create_queued(self, ddr_id, dates, commit=True):
        return self._rows

    async def create_failed_boundary(self, **kwargs):
        return None


class FakeDDR:
    def __init__(self, ddr_id="ddr-1", file_path="/tmp/ddr.pdf"):
        self.id = ddr_id
        self.file_path = file_path
        self.status = DDRStatus.QUEUED
        self.updated_at = 0


class FakeDDRRepository:
    def __init__(self, ddr: FakeDDR):
        self._ddr = ddr
        self.finalize_calls = []
        self.update_status_calls = []

    async def read_ddr_by_id(self, ddr_id):
        return self._ddr

    async def update_status(self, ddr, status, commit=True):
        self.update_status_calls.append(status)
        ddr.status = status
        return ddr

    async def finalize_status_from_dates(self, ddr, statuses):
        self.finalize_calls.append(list(statuses))
        s = list(statuses)
        if any(x == DDRDateStatus.SUCCESS for x in s):
            ddr.status = DDRStatus.COMPLETE
        else:
            ddr.status = DDRStatus.FAILED
        return ddr

    async def update_well_metadata(self, ddr, well_name, surface_location, commit=True):
        return ddr


class FakeCostService:
    def __init__(self):
        self.calls = []

    async def record_extraction_run(self, *, ddr_date_id, input_tokens, output_tokens, commit=True):
        self.calls.append(
            {
                "ddr_date_id": ddr_date_id,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "commit": commit,
            }
        )
        return SimpleNamespace(id="run-1")


class FakeEmbeddingService:
    def __init__(self):
        self.rows = []

    async def embed_successful_date(self, row):
        self.rows.append(row)


class FakeStatusStreamService:
    def __init__(self):
        self.started = []

    async def publish_date_started(self, ddr_id, date):
        self.started.append({"ddr_id": ddr_id, "date": date})

    async def publish_date_complete(self, *args, **kwargs):
        pass

    async def publish_date_failed(self, *args, **kwargs):
        pass

    async def publish_processing_complete(self, *args, **kwargs):
        pass


class FakeStorageService:
    def __init__(self):
        self.chunks: dict[str, bytes] = {}
        self.pdfs: dict[str, bytes] = {}

    async def upload_pdf(self, ddr_id: str, data: bytes) -> str:
        key = f"ces/ddrs/{ddr_id}/original.pdf"
        self.pdfs[key] = data
        return key

    async def upload_chunk(self, ddr_id: str, date: str, data: bytes) -> str:
        key = f"ces/ddrs/{ddr_id}/chunks/{date}.pdf"
        self.chunks[key] = data
        return key

    async def download(self, key: str) -> bytes:
        return self.pdfs.get(key, b"")

    async def download_original(self, ddr_id: str) -> bytes:
        key = f"ces/ddrs/{ddr_id}/original.pdf"
        return self.pdfs.get(key, b"")

    async def download_chunk(self, ddr_id: str, date: str) -> bytes:
        return self.chunks.get(f"ces/ddrs/{ddr_id}/chunks/{date}.pdf", b"%PDF-1.7")

    async def delete_ddr(self, ddr_id: str) -> None:
        prefix = f"ces/ddrs/{ddr_id}/"
        for k in list(self.chunks):
            if k.startswith(prefix):
                del self.chunks[k]
        for k in list(self.pdfs):
            if k.startswith(prefix):
                del self.pdfs[k]


def test_validator_accepts_valid_payload_and_preserves_order() -> None:
    validator = DDRExtractionValidator()
    result = validator.validate(FIXTURE_JSON)
    assert result.is_valid
    assert result.errors == []
    expected_activities = [row["activity"] for row in json.loads(FIXTURE_JSON)["time_logs"]]
    assert [row["activity"] for row in result.final_json["time_logs"]] == expected_activities


def test_validator_rejects_invalid_json() -> None:
    validator = DDRExtractionValidator()
    result = validator.validate("not-json")
    assert result.is_valid is False
    assert result.errors[0]["type"] == "json_decode_error"


def test_validator_rejects_schema_invalid_payload() -> None:
    validator = DDRExtractionValidator()
    bad = json.dumps(
        {
            "time_logs": [{"start_time": "00:00"}],
            "mud_records": [],
            "deviation_surveys": [],
            "bit_records": [],
        }
    )
    result = validator.validate(bad)
    assert result.is_valid is False
    assert result.final_json is None
    assert any("missing" in (err["type"] or "") for err in result.errors)


def test_extractor_returns_result_on_first_success() -> None:
    fake = FakeGeminiClient([ExtractionResult(text=FIXTURE_JSON, input_tokens=1, output_tokens=2)])
    extractor = GeminiDDRExtractor(client=fake, model="m", max_retries=2, sleep=lambda _s: asyncio.sleep(0))
    result = asyncio.run(extractor.extract(date="20240115", pdf_bytes=b"%PDF-1.7"))
    assert result.text == FIXTURE_JSON
    assert len(fake.calls) == 1


def test_extractor_retries_on_rate_limit_and_eventually_raises() -> None:
    sleeps: list[float] = []

    async def fake_sleep(seconds):
        sleeps.append(seconds)

    rate = type("RL", (Exception,), {})
    err = rate()
    err.status_code = 429
    fake = FakeGeminiClient([err, err, err, err])
    extractor = GeminiDDRExtractor(client=fake, model="m", max_retries=3, sleep=fake_sleep)

    raised = False
    try:
        asyncio.run(extractor.extract(date="20240115", pdf_bytes=b"x"))
    except RateLimitError:
        raised = True
    assert raised
    assert sleeps == [1.0, 2.0, 4.0, 8.0]
    assert len(fake.calls) == 4


def test_extractor_raises_extraction_error_on_non_rate_limit() -> None:
    fake = FakeGeminiClient([RuntimeError("server_blew_up")])
    extractor = GeminiDDRExtractor(client=fake, model="m", max_retries=3, sleep=lambda _s: asyncio.sleep(0))

    raised = False
    try:
        asyncio.run(extractor.extract(date="20240115", pdf_bytes=b"x"))
    except ExtractionError as exc:
        raised = True
        assert not isinstance(exc, RateLimitError)
    assert raised


def test_extractor_does_not_treat_generate_errors_as_rate_limits() -> None:
    sleeps: list[float] = []

    async def fake_sleep(seconds):
        sleeps.append(seconds)

    fake = FakeGeminiClient([RuntimeError("generate_content failed")])
    extractor = GeminiDDRExtractor(client=fake, model="m", max_retries=3, sleep=fake_sleep)

    raised = False
    try:
        asyncio.run(extractor.extract(date="20240115", pdf_bytes=b"x"))
    except ExtractionError as exc:
        raised = True
        assert not isinstance(exc, RateLimitError)
    assert raised
    assert sleeps == []


def test_pipeline_persists_success_warning_and_failure_per_date(tmp_path) -> None:
    pdf_path = tmp_path / "ddr.pdf"
    pdf_path.write_bytes(b"%PDF-1.7")

    rows = [FakeDDRDateRow("20240115"), FakeDDRDateRow("20240116"), FakeDDRDateRow("20240117")]
    date_repo = FakeDDRDateRepository(rows)
    ddr = FakeDDR(file_path=str(pdf_path))
    ddr_repo = FakeDDRRepository(ddr)

    rate = type("RL", (Exception,), {})
    rate_err = rate()
    rate_err.status_code = 429

    fake_client = FakeGeminiClient(
        [
            ExtractionResult(text=FIXTURE_JSON, input_tokens=100, output_tokens=200),
            ExtractionResult(text="{not-valid-json"),
            rate_err, rate_err, rate_err, rate_err,
        ]
    )
    extractor = GeminiDDRExtractor(client=fake_client, model="m", max_retries=3, sleep=lambda _s: asyncio.sleep(0))

    async def loader(_):
        return b"%PDF-1.7"

    async def fake_split(_):
        return SimpleNamespace(
            has_boundaries=True,
            date_chunks={"20240115": b"a", "20240116": b"b", "20240117": b"c"},
            raw_text_preview="",
        )

    splitter = SimpleNamespace(split_async=fake_split)
    cost_service = FakeCostService()
    embedding_service = FakeEmbeddingService()
    status_stream_service = FakeStatusStreamService()

    service = PreSplitPipelineService(
        ddr_repository=ddr_repo,
        ddr_date_repository=date_repo,
        pre_splitter=splitter,
        pdf_loader=loader,
        extractor=extractor,
        max_concurrent=2,
        extract_after_split=True,
        cost_service=cost_service,
        embedding_service=embedding_service,
        status_stream_service=status_stream_service,
        storage_service=FakeStorageService(),
    )

    asyncio.run(service.run("ddr-1"))

    statuses = {row.date: row.status for row in rows}
    assert statuses["20240115"] == DDRDateStatus.SUCCESS
    assert statuses["20240116"] == DDRDateStatus.FAILED
    assert statuses["20240117"] == DDRDateStatus.WARNING

    assert len(date_repo.success_calls) == 1
    assert date_repo.success_calls[0]["raw_response"]["text"] == FIXTURE_JSON
    assert cost_service.calls == [
        {"ddr_date_id": "row-20240115", "input_tokens": 100, "output_tokens": 200, "commit": False}
    ]
    assert len(embedding_service.rows) == 1
    assert embedding_service.rows[0].id == rows[0].id
    assert embedding_service.rows[0].ddr_id == rows[0].ddr_id
    assert embedding_service.rows[0].date == rows[0].date
    assert embedding_service.rows[0].final_json == rows[0].final_json

    failed = date_repo.failure_calls[0]
    assert failed["error_log"]["code"] == "VALIDATION_FAILED"
    assert failed["raw_response"] == {"text": "{not-valid-json"}

    warning = date_repo.warning_calls[0]
    assert warning["error_log"] == {"code": "RATE_LIMITED"}

    assert ddr_repo.finalize_calls, "parent finalize not called"
    final_set = set(ddr_repo.finalize_calls[-1])
    assert final_set == {DDRDateStatus.SUCCESS, DDRDateStatus.WARNING, DDRDateStatus.FAILED}
    assert ddr.status == DDRStatus.COMPLETE
    assert [event["date"] for event in status_stream_service.started] == ["20240115", "20240116", "20240117"]


def test_pipeline_marks_parent_failed_when_all_dates_fail(tmp_path) -> None:
    rows = [FakeDDRDateRow("20240115"), FakeDDRDateRow("20240116")]
    date_repo = FakeDDRDateRepository(rows)
    ddr = FakeDDR()
    ddr_repo = FakeDDRRepository(ddr)

    fake_client = FakeGeminiClient([RuntimeError("boom"), RuntimeError("boom")])
    extractor = GeminiDDRExtractor(client=fake_client, model="m", max_retries=0, sleep=lambda _s: asyncio.sleep(0))

    async def loader(_):
        return b"%PDF-1.7"

    async def fake_split(_):
        return SimpleNamespace(
            has_boundaries=True,
            date_chunks={"20240115": b"a", "20240116": b"b"},
            raw_text_preview="",
        )

    splitter = SimpleNamespace(split_async=fake_split)

    service = PreSplitPipelineService(
        ddr_repository=ddr_repo,
        ddr_date_repository=date_repo,
        pre_splitter=splitter,
        pdf_loader=loader,
        extractor=extractor,
        max_concurrent=2,
        extract_after_split=True,
        cost_service=FakeCostService(),
        embedding_service=FakeEmbeddingService(),
        storage_service=FakeStorageService(),
    )

    asyncio.run(service.run("ddr-1"))

    assert all(row.status == DDRDateStatus.FAILED for row in rows)
    assert ddr.status == DDRStatus.FAILED


def test_retry_date_waits_when_any_date_remains_queued() -> None:
    retry_row = FakeDDRDateRow("20240115")
    retry_row.status = DDRDateStatus.FAILED
    queued_row = FakeDDRDateRow("20240116")
    date_repo = FakeDDRDateRepository([retry_row, queued_row])
    ddr = FakeDDR()
    ddr_repo = FakeDDRRepository(ddr)
    fake_client = FakeGeminiClient([ExtractionResult(text=FIXTURE_JSON, input_tokens=1, output_tokens=2)])
    extractor = GeminiDDRExtractor(client=fake_client, model="m", max_retries=0, sleep=lambda _s: asyncio.sleep(0))
    service = PreSplitPipelineService(
        ddr_repository=ddr_repo,
        ddr_date_repository=date_repo,
        extractor=extractor,
        cost_service=FakeCostService(),
        embedding_service=FakeEmbeddingService(),
        occurrence_repository=SimpleNamespace(),
        storage_service=FakeStorageService(),
    )
    service._generate_occurrences = AsyncMock(return_value=1)

    row = asyncio.run(service.retry_date("ddr-1", "20240115"))

    assert row.status == DDRDateStatus.SUCCESS
    assert queued_row.status == DDRDateStatus.QUEUED
    assert ddr.status == DDRStatus.PROCESSING
    assert ddr_repo.finalize_calls == []
    service._generate_occurrences.assert_not_awaited()


def test_repository_finalize_is_complete_when_at_least_one_date_succeeds() -> None:
    from src.repository.crud.ddr import DDRCRUDRepository

    class FakeSession:
        def __init__(self):
            self.commits = 0

        def add(self, _):
            pass

        async def commit(self):
            self.commits += 1

        async def refresh(self, _):
            pass

    repo = DDRCRUDRepository(async_session=FakeSession())
    ddr = SimpleNamespace(status=DDRStatus.PROCESSING, updated_at=0)

    asyncio.run(repo.finalize_status_from_dates(ddr, [DDRDateStatus.FAILED, DDRDateStatus.SUCCESS]))
    assert ddr.status == DDRStatus.COMPLETE

    asyncio.run(repo.finalize_status_from_dates(ddr, [DDRDateStatus.FAILED, DDRDateStatus.FAILED]))
    assert ddr.status == DDRStatus.FAILED

    asyncio.run(repo.finalize_status_from_dates(ddr, [DDRDateStatus.WARNING]))
    assert ddr.status == DDRStatus.FAILED

    asyncio.run(repo.finalize_status_from_dates(ddr, []))
    assert ddr.status == DDRStatus.FAILED


def test_repository_mark_success_warning_failed_set_atomic_payload() -> None:
    from src.repository.crud.ddr import DDRDateCRUDRepository

    class FakeSession:
        def __init__(self):
            self.commits = 0

        def add(self, _):
            pass

        async def commit(self):
            self.commits += 1

        async def refresh(self, _):
            pass

    repo = DDRDateCRUDRepository(async_session=FakeSession())
    row = SimpleNamespace(status=DDRDateStatus.QUEUED, raw_response=None, final_json=None, error_log=None, updated_at=0)

    asyncio.run(repo.mark_success(row, raw_response={"text": "x"}, final_json={"time_logs": []}))
    assert row.status == DDRDateStatus.SUCCESS
    assert row.raw_response == {"text": "x"}
    assert row.final_json == {"time_logs": []}
    assert row.error_log is None

    asyncio.run(repo.mark_failed(row, error_log={"code": "VALIDATION_FAILED"}, raw_response={"text": "bad"}))
    assert row.status == DDRDateStatus.FAILED
    assert row.error_log == {"code": "VALIDATION_FAILED"}
    assert row.final_json is None

    asyncio.run(repo.mark_warning(row, error_log={"code": "RATE_LIMITED"}))
    assert row.status == DDRDateStatus.WARNING
    assert row.error_log == {"code": "RATE_LIMITED"}
    assert row.raw_response is None


def test_settings_load_gemini_api_key_through_settings_class() -> None:
    from src.config.settings.base import BackendBaseSettings

    s = BackendBaseSettings()
    assert hasattr(s, "GEMINI_API_KEY")
    assert hasattr(s, "GEMINI_MODEL")
    assert hasattr(s, "GEMINI_EXTRACTION_MAX_CONCURRENT")
    assert hasattr(s, "GEMINI_EXTRACTION_MAX_RETRIES")
    assert hasattr(s, "GEMINI_FLASH_LITE_INPUT_COST_PER_1M_TOKENS")
    assert hasattr(s, "GEMINI_FLASH_LITE_OUTPUT_COST_PER_1M_TOKENS")
    assert hasattr(s, "GEMINI_EMBEDDING_MODEL")
    assert hasattr(s, "GEMINI_EMBEDDING_DIMENSION")
    assert hasattr(s, "QDRANT_URL")
    assert hasattr(s, "QDRANT_API_KEY")
    assert hasattr(s, "QDRANT_COLLECTION_DDR_TIME_LOGS")
    assert hasattr(s, "LANGSMITH_TRACING")
    assert hasattr(s, "LANGSMITH_API_KEY")
    assert hasattr(s, "LANGSMITH_PROJECT")
    assert s.GEMINI_MODEL


def test_extractor_does_not_log_api_key_in_exception() -> None:
    fake = FakeGeminiClient([RuntimeError("connection refused")])
    extractor = GeminiDDRExtractor(client=fake, model="m", max_retries=0, sleep=lambda _s: asyncio.sleep(0))
    secret = "sk-do-not-leak-this-key-12345"
    raised_text = ""
    try:
        asyncio.run(extractor.extract(date="20240115", pdf_bytes=b"x"))
    except ExtractionError as exc:
        raised_text = str(exc) + " " + str(exc.detail)
    assert secret not in raised_text
