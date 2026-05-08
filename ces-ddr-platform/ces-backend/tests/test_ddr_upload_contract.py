import asyncio
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from fastapi import UploadFile
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from src.config.manager import settings
from src.config.settings.base import BackendBaseSettings
from src.main import backend_app
from src.securities.authorizations.jwt_authentication import jwt_authentication
from src.services.ddr import DDRUploadService, DDRUploadValidationError


class StubQueuedDDRRepository:
    def __init__(self) -> None:
        self.created = []
        self.ddrs = [
            SimpleNamespace(
                id="22222222-2222-2222-2222-222222222222",
                file_path="/app/uploads/new.pdf",
                status="queued",
                well_name="New Well",
                created_at=20,
            ),
            SimpleNamespace(
                id="11111111-1111-1111-1111-111111111111",
                file_path="/app/uploads/old.pdf",
                status="complete",
                well_name=None,
                created_at=10,
            ),
        ]

    async def create_queued_with_queue(self, **values):
        self.created.append(values)
        return SimpleNamespace(id=values["ddr_id"], status="queued", file_path=values["file_path"])

    async def read_all_descending(self):
        return self.ddrs

    async def read_by_id(self, ddr_id: str):
        return next((ddr for ddr in self.ddrs if ddr.id == ddr_id), None)


class FailingDDRRepository:
    async def create_queued_with_queue(self, **values):
        raise RuntimeError("db failed")


class StubProcessingQueueRepository:
    async def next_position(self) -> int:
        return 1


class StubDDRDateRepository:
    async def read_dates_by_ddr_id(self, ddr_id: str):
        return [
            SimpleNamespace(
                id="date-1",
                ddr_id=ddr_id,
                date="20240115",
                status="success",
                raw_response=None,
                final_json={"time_logs": []},
                error_log=None,
                created_at=1,
                updated_at=2,
            )
        ]


def make_upload(filename: str, content_type: str, content: bytes = b"%PDF-1.7") -> UploadFile:
    return UploadFile(filename=filename, file=BytesIO(content), headers={"content-type": content_type})


def test_upload_dir_setting_defaults_to_app_uploads() -> None:
    assert BackendBaseSettings().UPLOAD_DIR == "/app/uploads"


def test_upload_service_rejects_non_pdf_before_write(tmp_path) -> None:
    async def run() -> None:
        repository = StubQueuedDDRRepository()
        service = DDRUploadService(repository, StubProcessingQueueRepository(), upload_dir=str(tmp_path))
        upload = make_upload("field.txt", "text/plain")

        try:
            await service.upload(upload)
        except DDRUploadValidationError as exc:
            assert exc.detail == "only_pdf_files_accepted"
        else:
            raise AssertionError("expected validation error")

        assert repository.created == []
        assert list(tmp_path.iterdir()) == []

    asyncio.run(run())


def test_upload_service_rejects_spoofed_pdf_before_write(tmp_path) -> None:
    async def run() -> None:
        repository = StubQueuedDDRRepository()
        service = DDRUploadService(repository, StubProcessingQueueRepository(), upload_dir=str(tmp_path))
        upload = make_upload("field.pdf", "application/pdf", b"not-pdf")

        try:
            await service.upload(upload)
        except DDRUploadValidationError as exc:
            assert exc.detail == "only_pdf_files_accepted"
        else:
            raise AssertionError("expected validation error")

        assert repository.created == []
        assert list(tmp_path.iterdir()) == []

    asyncio.run(run())


def test_upload_service_saves_pdf_and_creates_queue_row(tmp_path, monkeypatch) -> None:
    async def run() -> None:
        repository = StubQueuedDDRRepository()
        service = DDRUploadService(repository, StubProcessingQueueRepository(), upload_dir=str(tmp_path))

        async def write_upload(_: UploadFile, file_path: Path) -> None:
            await asyncio.to_thread(file_path.write_bytes, b"%PDF-1.7")

        monkeypatch.setattr(service, "write_upload", write_upload)
        result = await service.upload(make_upload("FIELD.PDF", "application/pdf"))

        assert result.status == "queued"
        assert result.file_path.endswith(".pdf")
        assert Path(result.file_path).exists()
        assert repository.created[0]["processing_queue_repository"].__class__ is StubProcessingQueueRepository

    asyncio.run(run())


def test_upload_service_removes_partial_file_when_write_fails(tmp_path, monkeypatch) -> None:
    async def run() -> None:
        service = DDRUploadService(StubQueuedDDRRepository(), StubProcessingQueueRepository(), upload_dir=str(tmp_path))

        async def write_upload(_: UploadFile, file_path: Path) -> None:
            await asyncio.to_thread(file_path.write_bytes, b"%PDF-1.7")
            raise RuntimeError("write failed")

        monkeypatch.setattr(service, "write_upload", write_upload)

        try:
            await service.upload(make_upload("field.pdf", "application/pdf"))
        except RuntimeError as exc:
            assert str(exc) == "write failed"
        else:
            raise AssertionError("expected write failure")

        assert list(tmp_path.iterdir()) == []

    asyncio.run(run())


def test_upload_service_removes_file_when_db_insert_fails(tmp_path, monkeypatch) -> None:
    async def run() -> None:
        service = DDRUploadService(FailingDDRRepository(), StubProcessingQueueRepository(), upload_dir=str(tmp_path))

        async def write_upload(_: UploadFile, file_path: Path) -> None:
            await asyncio.to_thread(file_path.write_bytes, b"%PDF-1.7")

        monkeypatch.setattr(service, "write_upload", write_upload)

        try:
            await service.upload(make_upload("field.pdf", "application/pdf"))
        except RuntimeError as exc:
            assert str(exc) == "db failed"
        else:
            raise AssertionError("expected db failure")

        assert list(tmp_path.iterdir()) == []

    asyncio.run(run())


def override_auth() -> dict[str, str]:
    return {"user_id": "user-1"}


def ddr_dependency(route_path: str, dependency_name: str) -> Any:
    for route in backend_app.routes:
        if isinstance(route, APIRoute) and route.path == route_path:
            for dependency in route.dependant.dependencies:
                if dependency.name == dependency_name:
                    return dependency.call
    raise AssertionError(f"dependency `{dependency_name}` not found for `{route_path}`")


def test_upload_route_accepts_pdf_and_returns_queued(tmp_path, monkeypatch) -> None:
    repository = StubQueuedDDRRepository()
    previous_upload_dir = settings.UPLOAD_DIR
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))

    async def noop_dispatch(self: Any, ddr_id: str) -> None:
        pass

    monkeypatch.setattr(DDRUploadService, "dispatch_background", noop_dispatch)
    backend_app.dependency_overrides[jwt_authentication] = override_auth
    backend_app.dependency_overrides[ddr_dependency("/api/ddrs/upload", "ddr_repository")] = lambda: repository
    backend_app.dependency_overrides[
        ddr_dependency("/api/ddrs/upload", "processing_queue_repository")
    ] = StubProcessingQueueRepository

    try:
        response = TestClient(backend_app).post(
            "/api/ddrs/upload",
            files={"file": ("field.pdf", b"%PDF-1.7", "application/pdf")},
        )
    finally:
        backend_app.dependency_overrides.clear()
        monkeypatch.setattr(settings, "UPLOAD_DIR", previous_upload_dir)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "queued"
    assert repository.created[0]["ddr_id"] == body["id"]
    assert Path(repository.created[0]["file_path"]).exists()


def test_upload_route_rejects_non_pdf_without_file_write(tmp_path, monkeypatch) -> None:
    repository = StubQueuedDDRRepository()
    previous_upload_dir = settings.UPLOAD_DIR
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    backend_app.dependency_overrides[jwt_authentication] = override_auth
    backend_app.dependency_overrides[ddr_dependency("/api/ddrs/upload", "ddr_repository")] = lambda: repository
    backend_app.dependency_overrides[
        ddr_dependency("/api/ddrs/upload", "processing_queue_repository")
    ] = StubProcessingQueueRepository

    try:
        response = TestClient(backend_app).post(
            "/api/ddrs/upload",
            files={"file": ("field.txt", b"not-pdf", "text/plain")},
        )
    finally:
        backend_app.dependency_overrides.clear()
        monkeypatch.setattr(settings, "UPLOAD_DIR", previous_upload_dir)

    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["error_code"] == 400
    assert body["message"]["description"] == "only_pdf_files_accepted"
    assert repository.created == []
    assert list(tmp_path.iterdir()) == []


def test_list_ddrs_route_returns_descending_items() -> None:
    backend_app.dependency_overrides[jwt_authentication] = override_auth
    backend_app.dependency_overrides[ddr_dependency("/api/ddrs", "ddr_repository")] = StubQueuedDDRRepository

    try:
        response = TestClient(backend_app).get("/api/ddrs")
    finally:
        backend_app.dependency_overrides.clear()

    assert response.status_code == 200
    assert [item["created_at"] for item in response.json()] == [20, 10]


def test_get_ddr_route_returns_detail_or_not_found() -> None:
    backend_app.dependency_overrides[jwt_authentication] = override_auth
    backend_app.dependency_overrides[ddr_dependency("/api/ddrs/{ddr_id}", "ddr_repository")] = StubQueuedDDRRepository
    backend_app.dependency_overrides[
        ddr_dependency("/api/ddrs/{ddr_id}", "ddr_date_repository")
    ] = StubDDRDateRepository

    try:
        client = TestClient(backend_app)
        found = client.get("/api/ddrs/22222222-2222-2222-2222-222222222222")
        missing = client.get("/api/ddrs/33333333-3333-3333-3333-333333333333")
    finally:
        backend_app.dependency_overrides.clear()

    assert found.status_code == 200
    assert found.json()["id"] == "22222222-2222-2222-2222-222222222222"
    assert missing.status_code == 404
    body = missing.json()
    assert body["success"] is False
    assert body["error_code"] == 404
    assert body["message"]["description"] == "ddr_not_found"


def test_ddr_routes_require_authentication() -> None:
    response = TestClient(backend_app).get("/api/ddrs")

    assert response.status_code == 401


def test_openapi_includes_ddr_paths() -> None:
    schema = TestClient(backend_app).get("/openapi.json").json()

    assert "/api/auth/login" in schema["paths"]
    assert "/api/ddrs" in schema["paths"]
    assert "/api/ddrs/upload" in schema["paths"]
    assert "/api/ddrs/{ddr_id}" in schema["paths"]
