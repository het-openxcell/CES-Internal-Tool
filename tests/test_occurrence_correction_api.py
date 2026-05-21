import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from src.main import backend_app
from src.models.schemas.occurrence import OccurrenceCorrectionRequest
from src.securities.authorizations.jwt_authentication import jwt_authentication
from src.services.ddr import OccurrenceCorrectionService
from src.utilities.exceptions import EntityDoesNotExist, SecurityException


def _make_occurrence(**overrides):
    defaults = dict(
        id="occ-1",
        ddr_id="ddr-1",
        type="Stuck Pipe",
        section="Drilling",
        mmd=1500.0,
        density=None,
        notes=None,
        ddr_date_id="date-1",
        well_name="W1",
        surface_location=None,
        date="20260101",
        page_number=1,
        is_exported=False,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _make_user(user_id: str = "user-1"):
    return SimpleNamespace(id=user_id)


def _make_ddr(**overrides):
    defaults = dict(id="ddr-1", uploaded_by_user_id="user-1")
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class StubDDRRepo:
    def __init__(self, ddr=None):
        self._ddr = ddr if ddr is not None else _make_ddr()

    async def read_by_id(self, ddr_id: str):
        return self._ddr


class StubOccurrenceRepo:
    def __init__(self, occurrence=None):
        self._occurrence = occurrence
        self.updated = []
        self.committed = False
        self.refreshed = False
        self.async_session = self

    async def read_by_id(self, occurrence_id: str):
        return self._occurrence

    async def update(self, occurrence, values, commit: bool = True):
        for k, v in values.items():
            setattr(occurrence, k, v)
        self.updated.append(values)

    async def commit(self):
        self.committed = True

    async def refresh(self, occurrence):
        self.refreshed = True


class StubCorrectionRepo:
    def __init__(self):
        self.created = []

    async def create_correction(self, **kwargs):
        self.created.append(kwargs)


def test_patch_occurrence_happy_path() -> None:
    occurrence = _make_occurrence()
    ddr_repo = StubDDRRepo()
    occ_repo = StubOccurrenceRepo(occurrence)
    corr_repo = StubCorrectionRepo()
    service = OccurrenceCorrectionService(ddr_repo, occ_repo, corr_repo)
    user = _make_user()

    async def run():
        result = await service.patch_occurrence(
            occurrence_id="occ-1",
            field_name="type",
            corrected_value="Back Ream",
            reason="Text said backreamed",
            current_user=user,
        )
        return result

    result = asyncio.run(run())

    assert result.type == "Back Ream"
    assert len(corr_repo.created) == 1
    call = corr_repo.created[0]
    assert call["occurrence_id"] == "occ-1"
    assert call["ddr_id"] == "ddr-1"
    assert call["field_name"] == "type"
    assert call["original_value"] == "Stuck Pipe"
    assert call["corrected_value"] == "Back Ream"
    assert call["reason"] == "Text said backreamed"
    assert call["user_id"] == "user-1"
    assert call["commit"] is False
    assert occ_repo.committed is True
    assert occ_repo.refreshed is True


def test_patch_occurrence_404_when_not_found() -> None:
    ddr_repo = StubDDRRepo()
    occ_repo = StubOccurrenceRepo(occurrence=None)
    corr_repo = StubCorrectionRepo()
    service = OccurrenceCorrectionService(ddr_repo, occ_repo, corr_repo)

    async def run():
        await service.patch_occurrence(
            occurrence_id="missing",
            field_name="type",
            corrected_value="X",
            reason="Y",
            current_user=_make_user(),
        )

    with pytest.raises(EntityDoesNotExist):
        asyncio.run(run())

    assert len(corr_repo.created) == 0


def test_patch_occurrence_forbidden_when_user_does_not_own_ddr() -> None:
    ddr_repo = StubDDRRepo(_make_ddr(uploaded_by_user_id="other-user"))
    occ_repo = StubOccurrenceRepo(_make_occurrence())
    corr_repo = StubCorrectionRepo()
    service = OccurrenceCorrectionService(ddr_repo, occ_repo, corr_repo)

    async def run():
        await service.patch_occurrence(
            occurrence_id="occ-1",
            field_name="type",
            corrected_value="Back Ream",
            reason="Y",
            current_user=_make_user("user-1"),
        )

    with pytest.raises(SecurityException):
        asyncio.run(run())

    assert len(occ_repo.updated) == 0
    assert len(corr_repo.created) == 0


def test_patch_occurrence_invalid_field_name_raises_422() -> None:
    occurrence = _make_occurrence()
    ddr_repo = StubDDRRepo()
    occ_repo = StubOccurrenceRepo(occurrence)
    corr_repo = StubCorrectionRepo()
    service = OccurrenceCorrectionService(ddr_repo, occ_repo, corr_repo)

    async def run():
        await service.patch_occurrence(
            occurrence_id="occ-1",
            field_name="well_name",
            corrected_value="X",
            reason="Y",
            current_user=_make_user(),
        )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(run())

    assert exc_info.value.status_code == 422
    assert len(occ_repo.updated) == 0
    assert len(corr_repo.created) == 0


def test_patch_occurrence_numeric_field_casts_to_float() -> None:
    occurrence = _make_occurrence(mmd=1000.0)
    ddr_repo = StubDDRRepo()
    occ_repo = StubOccurrenceRepo(occurrence)
    corr_repo = StubCorrectionRepo()
    service = OccurrenceCorrectionService(ddr_repo, occ_repo, corr_repo)

    async def run():
        return await service.patch_occurrence(
            occurrence_id="occ-1",
            field_name="mmd",
            corrected_value="1500.5",
            reason="measured depth corrected",
            current_user=_make_user(),
        )

    result = asyncio.run(run())
    assert result.mmd == 1500.5
    assert corr_repo.created[0]["corrected_value"] == "1500.5"
    assert corr_repo.created[0]["original_value"] == "1000.0"


def test_patch_occurrence_non_finite_numeric_value_raises_422() -> None:
    ddr_repo = StubDDRRepo()
    occ_repo = StubOccurrenceRepo(_make_occurrence())
    corr_repo = StubCorrectionRepo()
    service = OccurrenceCorrectionService(ddr_repo, occ_repo, corr_repo)

    async def run():
        await service.patch_occurrence(
            occurrence_id="occ-1",
            field_name="density",
            corrected_value="nan",
            reason="Y",
            current_user=_make_user(),
        )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(run())

    assert exc_info.value.status_code == 422
    assert len(occ_repo.updated) == 0
    assert len(corr_repo.created) == 0


def test_patch_occurrence_invalid_section_raises_422() -> None:
    ddr_repo = StubDDRRepo()
    occ_repo = StubOccurrenceRepo(_make_occurrence())
    corr_repo = StubCorrectionRepo()
    service = OccurrenceCorrectionService(ddr_repo, occ_repo, corr_repo)

    async def run():
        await service.patch_occurrence(
            occurrence_id="occ-1",
            field_name="section",
            corrected_value="Not A Section",
            reason="Y",
            current_user=_make_user(),
        )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(run())

    assert exc_info.value.status_code == 422
    assert len(occ_repo.updated) == 0
    assert len(corr_repo.created) == 0


def test_patch_occurrence_non_numeric_value_for_numeric_field_raises_422() -> None:
    occurrence = _make_occurrence()
    ddr_repo = StubDDRRepo()
    occ_repo = StubOccurrenceRepo(occurrence)
    corr_repo = StubCorrectionRepo()
    service = OccurrenceCorrectionService(ddr_repo, occ_repo, corr_repo)

    async def run():
        await service.patch_occurrence(
            occurrence_id="occ-1",
            field_name="mmd",
            corrected_value="not-a-number",
            reason="Y",
            current_user=_make_user(),
        )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(run())

    assert exc_info.value.status_code == 422
    assert len(occ_repo.updated) == 0
    assert len(corr_repo.created) == 0


def test_occurrence_correction_request_rejects_empty_fields() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        OccurrenceCorrectionRequest(field_name="", corrected_value="X", reason="Y")

    with pytest.raises(ValidationError):
        OccurrenceCorrectionRequest(field_name="type", corrected_value="  ", reason="Y")

    with pytest.raises(ValidationError):
        OccurrenceCorrectionRequest(field_name="type", corrected_value="X", reason="")


def test_occurrence_correction_request_valid() -> None:
    req = OccurrenceCorrectionRequest(field_name="type", corrected_value="Back Ream", reason="typo")
    assert req.field_name == "type"
    assert req.corrected_value == "Back Ream"
    assert req.reason == "typo"
    assert not hasattr(req, "user_id")
    assert not hasattr(req, "ddr_id")


def _override_auth() -> dict:
    return {"user_id": "user-1"}


@pytest.fixture
def authed_client():
    backend_app.dependency_overrides[jwt_authentication] = _override_auth
    yield TestClient(backend_app)
    backend_app.dependency_overrides.clear()


def test_openapi_includes_occurrences_patch_path(authed_client) -> None:
    schema = authed_client.get("/openapi.json").json()
    assert "/api/occurrences/{occurrence_id}" in schema["paths"]


def test_patch_occurrence_route_requires_auth() -> None:
    client = TestClient(backend_app)
    resp = client.patch("/api/occurrences/occ-1", json={"field_name": "type", "corrected_value": "X", "reason": "Y"})
    assert resp.status_code == 401


def test_patch_occurrence_route_returns_422_on_empty_field(authed_client) -> None:
    from src.api.dependencies.services import get_occurrence_correction_service

    async def stub_service():
        pass

    backend_app.dependency_overrides[get_occurrence_correction_service] = stub_service
    resp = authed_client.patch(
        "/api/occurrences/occ-1",
        json={"field_name": "", "corrected_value": "X", "reason": "Y"},
    )
    assert resp.status_code == 422
    backend_app.dependency_overrides.pop(get_occurrence_correction_service, None)
