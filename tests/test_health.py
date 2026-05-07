from fastapi.testclient import TestClient

from src.main import backend_app


def test_health_returns_ok() -> None:
    response = TestClient(backend_app).get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
