import csv
import io
from unittest.mock import MagicMock

import pytest

from src.services.export.csv_timelogs import TimeLogCSVExportService


def _make_timelog(start: str, end: str, activity: str, comment: str, depth: float | None) -> dict:
    return {
        "start_time": start,
        "end_time": end,
        "activity": activity,
        "comment": comment,
        "depth_md": depth,
    }


def _parse_csv(buf: io.BytesIO) -> list[dict]:
    content = buf.read()
    assert content[:3] == b"\xef\xbb\xbf"
    text = content[3:].decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))
    return list(reader)


def test_generate_correct_row_count():
    service = TimeLogCSVExportService()
    data = [
        {"date": "20260101", "time_logs": [
            _make_timelog("06:00", "08:00", "Drilling", "Drilled", 1000.0),
            _make_timelog("08:00", "10:00", "Tripping", "Tripped out", 1100.0),
            _make_timelog("10:00", "12:00", "Ream", "Reamed", 1200.0),
        ]},
        {"date": "20260102", "time_logs": [
            _make_timelog("06:00", "07:00", "Circulating", "Circ", None),
            _make_timelog("07:00", "09:00", "Back Ream", "Back reamed", 1300.0),
            _make_timelog("09:00", "11:00", "Drilling", "Drilled more", 1400.0),
        ]},
    ]
    buf = service.generate(data)
    rows = _parse_csv(buf)
    assert len(rows) == 6


def test_output_starts_with_utf8_bom():
    service = TimeLogCSVExportService()
    buf = service.generate([])
    content = buf.read()
    assert content[:3] == b"\xef\xbb\xbf"


def test_columns_match_expected_header():
    service = TimeLogCSVExportService()
    data = [{"date": "20260101", "time_logs": [_make_timelog("06:00", "08:00", "Drilling", "Note", 1000.0)]}]
    buf = service.generate(data)
    rows = _parse_csv(buf)
    assert set(rows[0].keys()) == {"date", "time_from", "time_to", "activity", "details", "depth"}


def test_rows_sorted_by_date_then_time_from():
    service = TimeLogCSVExportService()
    data = [
        {"date": "20260102", "time_logs": [_make_timelog("08:00", "09:00", "Drilling", "", 1000.0)]},
        {"date": "20260101", "time_logs": [_make_timelog("07:00", "08:00", "Tripping", "", 900.0)]},
    ]
    buf = service.generate(data)
    rows = _parse_csv(buf)
    assert rows[0]["date"] == "20260101"
    assert rows[1]["date"] == "20260102"


@pytest.mark.anyio
async def test_export_timelogs_404_when_ddr_not_found(monkeypatch):
    from fastapi.testclient import TestClient

    from src.main import backend_app
    from src.securities.authorizations.jwt_authentication import jwt_authentication

    async def fake_read_by_id(self, id):
        return None

    monkeypatch.setattr("src.repository.crud.ddr.DDRCRUDRepository.read_by_id", fake_read_by_id)
    backend_app.dependency_overrides[jwt_authentication] = lambda: MagicMock(id="user-1")
    client = TestClient(backend_app)
    response = client.get("/api/export/timelogs/nonexistent-id")
    backend_app.dependency_overrides.clear()
    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


@pytest.mark.anyio
async def test_export_timelogs_404_when_no_processed_dates(monkeypatch):
    from fastapi.testclient import TestClient

    from src.main import backend_app
    from src.securities.authorizations.jwt_authentication import jwt_authentication

    async def fake_read_by_id(self, id):
        return MagicMock(file_path="uploads/test.pdf")

    async def fake_get_dates(self, ddr_id):
        return []

    monkeypatch.setattr("src.repository.crud.ddr.DDRCRUDRepository.read_by_id", fake_read_by_id)
    monkeypatch.setattr("src.repository.crud.ddr.DDRDateCRUDRepository.get_dates_with_timelogs", fake_get_dates)
    backend_app.dependency_overrides[jwt_authentication] = lambda: MagicMock(id="user-1")
    client = TestClient(backend_app)
    response = client.get("/api/export/timelogs/some-ddr-id")
    backend_app.dependency_overrides.clear()
    assert response.status_code == 404
    assert response.json()["error"] == "Well data not found"
