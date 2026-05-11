from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from src.main import backend_app
from src.securities.authorizations.jwt_authentication import jwt_authentication
from src.services.keywords.loader import KeywordLoader


def override_auth() -> dict[str, str]:
    return {"user_id": "user-1"}


@pytest.fixture
def client() -> TestClient:
    return TestClient(backend_app)


@pytest.fixture
def authed_client() -> Generator[TestClient, None, None]:
    backend_app.dependency_overrides[jwt_authentication] = override_auth
    yield TestClient(backend_app)
    backend_app.dependency_overrides.clear()
    KeywordLoader.load()


def test_put_keywords_requires_authentication(client: TestClient) -> None:
    response = client.put("/api/keywords", json={"stuck pipe": "Stuck Pipe"})
    assert response.status_code == 401


def test_put_keywords_reloads_in_memory_store(authed_client: TestClient) -> None:
    new_keywords = {"custom keyword": "Stuck Pipe", "another key": "Lost Circulation"}
    response = authed_client.put("/api/keywords", json=new_keywords)
    assert response.status_code == 200
    assert response.json() == {"updated": 2}
    assert KeywordLoader.get_keywords() == new_keywords


def test_put_keywords_empty_dict_accepted(authed_client: TestClient) -> None:
    response = authed_client.put("/api/keywords", json={})
    assert response.status_code == 200
    assert response.json() == {"updated": 0}


def test_put_keywords_rejects_invalid_occurrence_type(authed_client: TestClient) -> None:
    response = authed_client.put("/api/keywords", json={"blowout": "NotARealType"})
    assert response.status_code == 422


def test_put_keywords_rejects_oversized_payload(authed_client: TestClient) -> None:
    big_payload = {f"keyword_{i}": "Stuck Pipe" for i in range(1001)}
    response = authed_client.put("/api/keywords", json=big_payload)
    assert response.status_code == 400


def test_openapi_includes_keywords_path(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    assert "/api/keywords" in schema["paths"]
