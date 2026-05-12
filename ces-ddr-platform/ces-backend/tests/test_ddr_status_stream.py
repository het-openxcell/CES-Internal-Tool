import asyncio
import json
from types import SimpleNamespace
from typing import Any

from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from src.main import backend_app
from src.models.schemas.ddr import DDRDateFailedEvent, DDRProcessingCompleteEvent
from src.securities.authorizations.jwt_authentication import stream_query_token_authentication
from src.services.pipeline.extract import ExtractionResult
from src.services.pipeline_service import PreSplitPipelineService
from src.services.processing_status import ProcessingStatusStreamService


class StubDDRRepository:
    def __init__(self) -> None:
        self.ddrs = {
            "ddr-1": SimpleNamespace(id="ddr-1", status="processing", file_path="/tmp/ddr-1.pdf", created_at=1),
            "ddr-2": SimpleNamespace(id="ddr-2", status="complete", file_path="/tmp/ddr-2.pdf", created_at=2),
        }

    async def read_by_id(self, ddr_id: str) -> Any:
        return self.ddrs.get(ddr_id)

    async def read_ddr_by_id(self, ddr_id: str) -> Any:
        return self.ddrs[ddr_id]

    async def finalize_status_from_dates(self, ddr: Any, statuses: Any) -> Any:
        ddr.status = "complete" if "success" in list(statuses) else "failed"
        return ddr

    async def update_well_metadata(self, ddr: Any, well_name: Any, surface_location: Any, commit: bool = True) -> Any:
        return ddr


class StubDDRDateRepository:
    def __init__(self) -> None:
        self.rows = [
            SimpleNamespace(id="date-1", ddr_id="ddr-1", date="20241031", status="queued", error_log=None),
            SimpleNamespace(id="date-2", ddr_id="ddr-1", date="20241101", status="queued", error_log=None),
        ]
        self.success_calls = []
        self.failed_calls = []

    async def read_dates_by_ddr_id(self, ddr_id: str) -> list[Any]:
        return [row for row in self.rows if row.ddr_id == ddr_id]

    async def mark_success(self, row: Any, raw_response: Any, final_json: Any, commit: bool = True) -> Any:
        self.success_calls.append(row.date)
        row.status = "success"
        row.raw_response = raw_response
        row.final_json = final_json
        return row

    async def mark_failed(self, row: Any, error_log: Any, raw_response: Any = None) -> Any:
        self.failed_calls.append(row.date)
        row.status = "failed"
        row.error_log = error_log
        row.raw_response = raw_response
        return row


class StubRequest:
    async def is_disconnected(self) -> bool:
        return False


class StubExtractor:
    def __init__(self, outcomes: dict[str, Any]) -> None:
        self.outcomes = outcomes

    async def extract(self, date: str, pdf_bytes: bytes) -> Any:
        outcome = self.outcomes[date]
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


class StubValidator:
    def validate(self, text: str) -> Any:
        return SimpleNamespace(is_valid=True, final_json={"date": text}, errors=[])


class StubCostService:
    async def record_extraction_run(self, *, ddr_date_id, input_tokens, output_tokens, commit=True) -> Any:
        return SimpleNamespace(id="run-1")


class StubEmbeddingService:
    async def embed_successful_date(self, row: Any) -> None:
        return None


def override_auth() -> dict[str, str]:
    return {"user_id": "user-1"}


def ddr_dependency(route_path: str, dependency_name: str) -> Any:
    for route in backend_app.routes:
        if isinstance(route, APIRoute) and route.path == route_path:
            for dependency in route.dependant.dependencies:
                if dependency.name == dependency_name:
                    return dependency.call
    raise AssertionError(f"dependency `{dependency_name}` not found for `{route_path}`")


def test_status_event_payload_contracts() -> None:
    failed = DDRDateFailedEvent(date="20241031", error="Tour Sheet Serial not detected", raw_response_id="date-1")
    complete = DDRProcessingCompleteEvent(total_dates=30, failed_dates=2, warning_dates=1, total_occurrences=0)

    assert failed.model_dump() == {
        "date": "20241031",
        "error": "Tour Sheet Serial not detected",
        "raw_response_id": "date-1",
    }
    assert complete.model_dump() == {
        "total_dates": 30,
        "failed_dates": 2,
        "warning_dates": 1,
        "total_occurrences": 0,
    }


def test_stream_service_formats_sse_frames_and_closes_on_complete() -> None:
    async def run() -> None:
        service = ProcessingStatusStreamService()
        generator = service.stream("ddr-1", StubRequest())
        await service.publish_date_complete("ddr-1", date="20241031", occurrences_count=0)
        await service.publish_processing_complete(
            "ddr-1",
            total_dates=1,
            failed_dates=0,
            warning_dates=0,
            total_occurrences=0,
        )

        first = await asyncio.wait_for(generator.__anext__(), timeout=1)
        second = await asyncio.wait_for(generator.__anext__(), timeout=1)

        assert first == 'event: date_complete\ndata: {"date":"20241031","status":"success","occurrences_count":0}\n\n'
        assert second == (
            'event: processing_complete\n'
            'data: {"total_dates":1,"failed_dates":0,"warning_dates":0,"total_occurrences":0}\n\n'
        )

        try:
            await asyncio.wait_for(generator.__anext__(), timeout=1)
        except StopAsyncIteration:
            pass
        else:
            raise AssertionError("stream should close after processing_complete")

    asyncio.run(run())


def test_status_stream_route_requires_auth_and_returns_not_found_shape() -> None:
    repository = StubDDRRepository()
    backend_app.dependency_overrides[ddr_dependency("/api/ddrs/{ddr_id}/status/stream", "ddr_repository")] = (
        lambda: repository
    )
    backend_app.dependency_overrides[
        ddr_dependency("/api/ddrs/{ddr_id}/status/stream", "ddr_date_repository")
    ] = StubDDRDateRepository

    try:
        client = TestClient(backend_app)
        unauthorized = client.get("/api/ddrs/ddr-1/status/stream")
        backend_app.dependency_overrides[stream_query_token_authentication] = override_auth
        missing = client.get("/api/ddrs/unknown/status/stream")
    finally:
        backend_app.dependency_overrides.clear()

    assert unauthorized.status_code == 401
    assert missing.status_code == 404
    assert missing.json() == {"error": "DDR not found", "code": "NOT_FOUND", "details": {}}


def test_status_stream_route_returns_event_stream_headers() -> None:
    service = ProcessingStatusStreamService()
    repository = StubDDRRepository()
    date_repository = StubDDRDateRepository()
    date_repository.rows = [
        SimpleNamespace(id="date-3", ddr_id="ddr-2", date="20241031", status="success", error_log=None)
    ]
    backend_app.dependency_overrides[stream_query_token_authentication] = override_auth
    backend_app.dependency_overrides[ddr_dependency("/api/ddrs/{ddr_id}/status/stream", "ddr_repository")] = (
        lambda: repository
    )
    backend_app.dependency_overrides[
        ddr_dependency("/api/ddrs/{ddr_id}/status/stream", "ddr_date_repository")
    ] = lambda: date_repository
    backend_app.state.processing_status_stream_service = service

    try:
        client = TestClient(backend_app)
        with client.stream("GET", "/api/ddrs/ddr-2/status/stream") as response:
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/event-stream")
            assert response.headers["cache-control"] == "no-cache"
    finally:
        backend_app.dependency_overrides.clear()
        if hasattr(backend_app.state, "processing_status_stream_service"):
            delattr(backend_app.state, "processing_status_stream_service")


def test_pipeline_publishes_events_after_repository_writes_and_finalizes_counts() -> None:
    async def run() -> None:
        ddr_repository = StubDDRRepository()
        date_repository = StubDDRDateRepository()
        service = ProcessingStatusStreamService()
        events = []

        async def capture(ddr_id: str, event_name: str, payload: Any) -> None:
            events.append((event_name, json.loads(payload.model_dump_json())))

        service.publish = capture
        pipeline = PreSplitPipelineService(
            ddr_repository=ddr_repository,
            ddr_date_repository=date_repository,
            extractor=StubExtractor(
                {
                    "20241031": ExtractionResult(text="20241031"),
                    "20241101": ExtractionResult(text="20241101"),
                }
            ),
            validator=StubValidator(),
            status_stream_service=service,
            cost_service=StubCostService(),
            embedding_service=StubEmbeddingService(),
        )

        await pipeline._extract_all_dates(
            ddr_id="ddr-1",
            ddr=ddr_repository.ddrs["ddr-1"],
            date_chunks={"20241031": b"one", "20241101": b"two"},
        )

        assert date_repository.success_calls == ["20241031", "20241101"]
        assert [event[0] for event in events] == ["date_complete", "date_complete", "processing_complete"]
        assert events[-1][1] == {
            "total_dates": 2,
            "failed_dates": 0,
            "warning_dates": 0,
            "total_occurrences": 0,
        }

    asyncio.run(run())
