from decimal import Decimal
from types import SimpleNamespace
from typing import Any

from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from src.main import backend_app
from src.securities.authorizations.jwt_authentication import jwt_authentication


class StubPipelineRunRepository:
    async def aggregate_all_time_cost(self):
        return SimpleNamespace(total_cost_usd=Decimal("0.123456"), total_runs=12)


def override_auth() -> dict[str, str]:
    return {"user_id": "user-1"}


def route_dependency(route_path: str, dependency_name: str) -> Any:
    for route in backend_app.routes:
        if isinstance(route, APIRoute) and route.path == route_path:
            for dependency in route.dependant.dependencies:
                if dependency.name == dependency_name:
                    return dependency.call
    raise AssertionError(f"dependency `{dependency_name}` not found for `{route_path}`")


def test_pipeline_cost_route_requires_authentication() -> None:
    response = TestClient(backend_app).get("/api/pipeline/cost")

    assert response.status_code == 401


def test_pipeline_cost_route_returns_all_time_aggregate() -> None:
    backend_app.dependency_overrides[jwt_authentication] = override_auth
    backend_app.dependency_overrides[
        route_dependency("/api/pipeline/cost", "pipeline_run_repository")
    ] = StubPipelineRunRepository

    try:
        response = TestClient(backend_app).get("/api/pipeline/cost")
    finally:
        backend_app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "total_cost_usd": "0.123456",
        "total_runs": 12,
        "period": "all_time",
    }


def test_openapi_includes_pipeline_cost_path() -> None:
    schema = TestClient(backend_app).get("/openapi.json").json()

    assert "/api/pipeline/cost" in schema["paths"]
