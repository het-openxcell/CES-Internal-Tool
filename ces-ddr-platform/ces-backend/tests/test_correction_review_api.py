import asyncio
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.models.schemas.correction import CorrectionPageResponse, CorrectionReviewItem
from src.services.correction.review import CorrectionReviewService

VALID_DDR_ID = "11111111-1111-1111-1111-111111111111"


def _make_correction(**overrides):
    defaults = dict(
        id="corr-1",
        occurrence_id="occ-1",
        ddr_id="ddr-1",
        field_name="type",
        original_value="old",
        corrected_value="new",
        reason="reviewed",
        user_id="user-1",
        created_at=1700000000,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class StubCorrectionReviewRepo:
    def __init__(self, rows=None, total=0):
        self.rows = rows if rows is not None else []
        self.total = total
        self.get_all_calls = []
        self.count_all_calls = []

    async def get_all(self, **kwargs):
        self.get_all_calls.append(kwargs)
        return self.rows

    async def count_all(self, **kwargs):
        self.count_all_calls.append(kwargs)
        return self.total


def test_correction_review_service_happy_path_maps_page_response_without_user_id() -> None:
    rows = [_make_correction(id=f"corr-{i}", occurrence_id=f"occ-{i}") for i in range(3)]
    repo = StubCorrectionReviewRepo(rows=rows, total=7)
    service = CorrectionReviewService(repo)

    async def run():
        return await service.list_corrections(field_name=None, ddr_id=None, page=1, page_size=3)

    response = asyncio.run(run())

    assert len(response.items) == 3
    assert response.total == 7
    assert response.page == 1
    assert response.page_size == 3
    assert set(response.items[0].model_dump().keys()) == {
        "id",
        "occurrence_id",
        "ddr_id",
        "field_name",
        "original_value",
        "corrected_value",
        "reason",
        "created_at",
    }
    assert "user_id" not in response.items[0].model_dump()


def test_correction_review_service_forwards_filters_to_items_and_count() -> None:
    repo = StubCorrectionReviewRepo(rows=[], total=0)
    service = CorrectionReviewService(repo)

    async def run():
        return await service.list_corrections(field_name="type", ddr_id="ddr-1", page=1, page_size=50)

    asyncio.run(run())

    assert repo.get_all_calls == [{"field_name": "type", "ddr_id": "ddr-1", "limit": 50, "offset": 0}]
    assert repo.count_all_calls == [{"field_name": "type", "ddr_id": "ddr-1"}]


def test_correction_review_service_pagination_uses_page_offset() -> None:
    repo = StubCorrectionReviewRepo(rows=[], total=0)
    service = CorrectionReviewService(repo)

    async def run():
        return await service.list_corrections(field_name=None, ddr_id=None, page=2, page_size=50)

    response = asyncio.run(run())

    assert repo.get_all_calls == [{"field_name": None, "ddr_id": None, "limit": 50, "offset": 50}]
    assert response.page == 2
    assert response.page_size == 50


def test_correction_review_service_empty_response() -> None:
    repo = StubCorrectionReviewRepo(rows=[], total=0)
    service = CorrectionReviewService(repo)

    async def run():
        return await service.list_corrections(field_name=None, ddr_id=None, page=1, page_size=50)

    response = asyncio.run(run())

    assert response.items == []
    assert response.total == 0
    assert response.page == 1
    assert response.page_size == 50


class StubCorrectionReviewService:
    def __init__(self):
        self.calls = []

    async def list_corrections(self, field_name, ddr_id, page, page_size):
        self.calls.append({"field_name": field_name, "ddr_id": ddr_id, "page": page, "page_size": page_size})
        return CorrectionPageResponse(
            items=[
                CorrectionReviewItem(
                    id="corr-1",
                    occurrence_id="occ-1",
                    ddr_id=VALID_DDR_ID,
                    field_name="type",
                    original_value="old",
                    corrected_value="new",
                    reason="reviewed",
                    created_at=1700000000,
                )
            ],
            total=7,
            page=page,
            page_size=page_size,
        )


def _override_auth() -> dict:
    return {"user_id": "user-1"}


@pytest.fixture
def correction_route_client():
    from src.api.dependencies.services import get_correction_review_service
    from src.api.routes.v1.corrections import router as corrections_router
    from src.securities.authorizations.jwt_authentication import jwt_authentication

    app = FastAPI()
    service = StubCorrectionReviewService()
    app.include_router(corrections_router, prefix="/api")
    app.dependency_overrides[jwt_authentication] = _override_auth
    app.dependency_overrides[get_correction_review_service] = lambda: service
    yield TestClient(app), service
    app.dependency_overrides.clear()


def test_get_corrections_route_returns_paginated_envelope(correction_route_client) -> None:
    client, service = correction_route_client

    response = client.get(f"/api/corrections?field_name=type&ddr_id={VALID_DDR_ID}&page=2&page_size=50")

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "id": "corr-1",
                "occurrence_id": "occ-1",
                "ddr_id": VALID_DDR_ID,
                "field_name": "type",
                "original_value": "old",
                "corrected_value": "new",
                "reason": "reviewed",
                "created_at": 1700000000,
            }
        ],
        "summaries": [],
        "total": 7,
        "page": 2,
        "page_size": 50,
    }
    assert service.calls == [{"field_name": "type", "ddr_id": VALID_DDR_ID, "page": 2, "page_size": 50}]


def test_get_corrections_route_rejects_malformed_ddr_id(correction_route_client) -> None:
    client, service = correction_route_client

    response = client.get("/api/corrections?ddr_id=not-a-uuid")

    assert response.status_code == 422
    assert service.calls == []


def test_get_corrections_route_requires_auth() -> None:
    from src.api.dependencies.services import get_correction_review_service
    from src.api.routes.v1.corrections import router as corrections_router
    from src.utilities.exceptions.exceptions import AuthorizationHeaderException, authorization_header_exception_handler

    app = FastAPI()
    app.add_exception_handler(AuthorizationHeaderException, authorization_header_exception_handler)
    app.include_router(corrections_router, prefix="/api")
    app.dependency_overrides[get_correction_review_service] = lambda: StubCorrectionReviewService()
    client = TestClient(app)

    response = client.get("/api/corrections")

    assert response.status_code == 401


def test_backend_app_openapi_includes_corrections_path() -> None:
    from src.main import backend_app

    client = TestClient(backend_app)
    schema = client.get("/openapi.json").json()

    assert "/api/corrections" in schema["paths"]


def test_backend_app_corrections_route_uses_registered_dependencies() -> None:
    from src.api.dependencies.services import get_correction_review_service
    from src.main import backend_app
    from src.securities.authorizations.jwt_authentication import jwt_authentication

    service = StubCorrectionReviewService()
    backend_app.dependency_overrides[jwt_authentication] = _override_auth
    backend_app.dependency_overrides[get_correction_review_service] = lambda: service
    try:
        client = TestClient(backend_app)

        response = client.get("/api/corrections")

        assert response.status_code == 200
        assert response.json()["total"] == 7
        assert service.calls == [{"field_name": None, "ddr_id": None, "page": 1, "page_size": 50}]
    finally:
        backend_app.dependency_overrides.clear()
