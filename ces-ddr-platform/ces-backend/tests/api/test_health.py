from fastapi.testclient import TestClient

from app.main import AppFactory


def test_health_returns_ok_status() -> None:
    client = TestClient(AppFactory().create())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
