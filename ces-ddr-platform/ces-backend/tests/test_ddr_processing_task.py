import asyncio
from types import SimpleNamespace
from typing import Any

from src.services.pipeline_service import PreSplitPipelineService


class StubDDRRepository:
    def __init__(self, ddr: SimpleNamespace) -> None:
        self.ddr = ddr
        self.status_updates: list[str] = []
        self.finalize_calls: list[list[str]] = []

    async def read_ddr_by_id(self, ddr_id: str) -> SimpleNamespace:
        assert ddr_id == self.ddr.id
        return self.ddr

    async def update_status(self, ddr: SimpleNamespace, status: str, commit: bool = True) -> SimpleNamespace:
        self.status_updates.append(status)
        ddr.status = status
        return ddr

    async def finalize_status_from_dates(self, ddr: SimpleNamespace, statuses: Any) -> SimpleNamespace:
        self.finalize_calls.append(list(statuses))
        return ddr


class StubDDRDateRepository:
    def __init__(self) -> None:
        self.bulk_calls: list[dict[str, Any]] = []
        self.failed_calls: list[dict[str, Any]] = []
        self._rows: list[SimpleNamespace] = []

    async def bulk_create_queued(
        self,
        ddr_id: str,
        dates: Any,
        commit: bool = True,
    ) -> list[SimpleNamespace]:
        materialized = list(dates)
        self.bulk_calls.append({"ddr_id": ddr_id, "dates": materialized})
        self._rows = [
            SimpleNamespace(ddr_id=ddr_id, date=d, status="queued", source_page_numbers=None)
            for d in materialized
        ]
        return list(self._rows)

    async def read_dates_by_ddr_id(self, ddr_id: str) -> list[SimpleNamespace]:
        return list(self._rows)

    async def mark_success(self, row: Any, raw_response: Any, final_json: Any) -> Any:
        row.status = "success"
        return row

    async def mark_failed(self, row: Any, error_log: Any, raw_response: Any = None) -> Any:
        row.status = "failed"
        return row

    async def mark_warning(self, row: Any, error_log: Any, raw_response: Any = None) -> Any:
        row.status = "warning"
        return row

    async def bulk_update_source_page_numbers(
        self,
        ddr_id: str,
        date_page_numbers: dict[str, list[int]],
        commit: bool = True,
    ):
        for row in self._rows:
            if row.date in date_page_numbers:
                row.source_page_numbers = date_page_numbers[row.date]
        return list(self._rows)

    async def create_failed_boundary(
        self, ddr_id: str, date: str, reason: str, raw_page_content: str, commit: bool = True
    ) -> SimpleNamespace:
        self.failed_calls.append(
            {"ddr_id": ddr_id, "date": date, "reason": reason, "raw_page_content": raw_page_content}
        )
        return SimpleNamespace(
            ddr_id=ddr_id,
            date=date,
            status="failed",
            error_log={"reason": reason, "raw_page_content": raw_page_content},
        )


class StubSplitter:
    def __init__(self, result: Any) -> None:
        self._result = result

    async def split_async(self, source: Any) -> Any:
        return self._result


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

    async def delete_ddr(self, ddr_id: str) -> None:
        prefix = f"ces/ddrs/{ddr_id}/"
        for k in list(self.chunks):
            if k.startswith(prefix):
                del self.chunks[k]
        for k in list(self.pdfs):
            if k.startswith(prefix):
                del self.pdfs[k]


def _split_result(
    date_chunks: dict[str, bytes],
    raw_text_preview: str = "",
    page_dates: dict[int, list[str]] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        date_chunks=date_chunks,
        page_dates=page_dates or {},
        warnings=[],
        raw_text_preview=raw_text_preview,
        has_boundaries=bool(date_chunks),
    )


def test_pipeline_service_creates_queued_dates_and_marks_processing(tmp_path) -> None:
    async def run() -> None:
        ddr = SimpleNamespace(id="ddr-1", file_path=str(tmp_path / "x.pdf"), status="queued")
        ddr_repo = StubDDRRepository(ddr)
        date_repo = StubDDRDateRepository()
        result = _split_result(
            {"20240115": b"%PDF-bytes-1", "20240116": b"%PDF-bytes-2"},
            page_dates={1: ["20240115"], 2: ["20240115", "20240116"]},
        )

        service = PreSplitPipelineService(
            ddr_repository=ddr_repo,
            ddr_date_repository=date_repo,
            pre_splitter=StubSplitter(result),
            pdf_loader=lambda path: _async_return(b"%PDF-1.7"),
            extract_after_split=False,
            storage_service=FakeStorageService(),
        )

        await service.run("ddr-1")

        assert ddr_repo.status_updates == ["processing"]
        assert ddr_repo.finalize_calls == []
        assert date_repo.bulk_calls == [{"ddr_id": "ddr-1", "dates": ["20240115", "20240116"]}]
        assert {row.date: row.source_page_numbers for row in date_repo._rows} == {
            "20240115": [1, 2],
            "20240116": [2],
        }
        assert date_repo.failed_calls == []

    asyncio.run(run())


def test_pipeline_service_records_no_boundary_failure() -> None:
    async def run() -> None:
        ddr = SimpleNamespace(id="ddr-2", file_path="/tmp/x.pdf", status="queued")
        ddr_repo = StubDDRRepository(ddr)
        date_repo = StubDDRDateRepository()
        result = _split_result({}, raw_text_preview="non-standard contractor header")

        service = PreSplitPipelineService(
            ddr_repository=ddr_repo,
            ddr_date_repository=date_repo,
            pre_splitter=StubSplitter(result),
            pdf_loader=lambda path: _async_return(b"%PDF-1.7"),
            extract_after_split=False,
        )

        await service.run("ddr-2")

        assert ddr_repo.status_updates == ["failed"]
        assert date_repo.bulk_calls == []
        assert len(date_repo.failed_calls) == 1
        failure = date_repo.failed_calls[0]
        assert failure["reason"] == "No date boundaries detected"
        assert failure["raw_page_content"] == "non-standard contractor header"
        assert failure["date"] == PreSplitPipelineService.no_boundary_placeholder_date

    asyncio.run(run())


async def _async_return(value: Any) -> Any:
    return value
