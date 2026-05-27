from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from src.main import backend_app
from src.securities.authorizations.jwt_authentication import jwt_authentication


def make_user(user_id: str, email: str, is_active: bool, role_names: list[str]):
    roles = [SimpleNamespace(name=r) for r in role_names]
    return SimpleNamespace(
        id=user_id,
        email=email,
        is_active=is_active,
        roles=roles,
        password_hash="hash",
        created_at=1000000,
        updated_at=1000000,
    )


ADMIN_USER = make_user("admin-id", "admin@example.com", True, ["ADMIN"])
REGULAR_USER = make_user("user-id", "bob@example.com", True, ["USER"])


def override_admin_auth():
    return ADMIN_USER


def override_user_auth():
    return REGULAR_USER


class StubUserRepo:
    def __init__(self):
        self._users = [
            make_user("admin-id", "admin", True, ["ADMIN"]),
            make_user("user-id", "bob", True, ["USER"]),
        ]

    async def read_all_with_roles(self):
        return self._users

    async def find_by_email(self, email: str):
        for u in self._users:
            if u.email == email:
                return u
        return None

    async def create_user(self, email: str, password_hash: str, is_active: bool = True):
        new = make_user(f"new-id-{email}", email, is_active, [])
        self._users.append(new)
        return new

    async def assign_role(self, user, role):
        user.roles.append(SimpleNamespace(name=role.name))

    async def deactivate(self, user):
        user.is_active = False
        user.updated_at = 9999999
        return user

    async def read_user_with_roles(self, user_id: str):
        for u in self._users:
            if u.id == user_id:
                return u
        return None


class StubRoleRepo:
    async def find_by_name(self, name: str):
        return SimpleNamespace(id="00000000-0000-0000-0000-000000000001", name=name)


def find_all_route_dependencies(dependency_name: str) -> list[Any]:
    found = []
    for route in backend_app.routes:
        if isinstance(route, APIRoute):
            for dep in route.dependant.dependencies:
                if dep.name == dependency_name:
                    found.append(dep.call)
    return found


def apply_repo_overrides():
    for dep_call in find_all_route_dependencies("user_repository"):
        backend_app.dependency_overrides[dep_call] = StubUserRepo
    for dep_call in find_all_route_dependencies("role_repository"):
        backend_app.dependency_overrides[dep_call] = StubRoleRepo


@pytest.fixture
def client() -> TestClient:
    return TestClient(backend_app)


@pytest.fixture
def admin_client():
    backend_app.dependency_overrides[jwt_authentication] = override_admin_auth
    apply_repo_overrides()
    yield TestClient(backend_app)
    backend_app.dependency_overrides.clear()


def test_get_users_requires_auth(client: TestClient) -> None:
    response = client.get("/api/users")
    assert response.status_code == 401


def test_get_users_non_admin_gets_403(client: TestClient) -> None:
    backend_app.dependency_overrides[jwt_authentication] = override_user_auth
    try:
        response = client.get("/api/users")
    finally:
        backend_app.dependency_overrides.clear()
    assert response.status_code == 403


def test_get_users_returns_safe_fields(admin_client: TestClient) -> None:
    response = admin_client.get("/api/users")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    for user in data:
        assert "password_hash" not in user
        assert "id" in user
        assert "email" in user
        assert "is_active" in user
        assert "roles" in user


def test_post_users_requires_auth(client: TestClient) -> None:
    response = client.post("/api/users", json={"email": "newuser@example.com", "password": "strongpass"})
    assert response.status_code == 401


def test_post_users_non_admin_gets_403(client: TestClient) -> None:
    backend_app.dependency_overrides[jwt_authentication] = override_user_auth
    try:
        response = client.post("/api/users", json={"email": "newuser@example.com", "password": "strongpass"})
    finally:
        backend_app.dependency_overrides.clear()
    assert response.status_code == 403


def test_post_users_creates_user(admin_client: TestClient) -> None:
    response = admin_client.post("/api/users", json={"email": "newuser@example.com", "password": "strongpass"})
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["is_active"] is True
    assert isinstance(data["roles"], list)
    assert "id" in data
    assert "password_hash" not in data


def test_post_users_short_password_rejected(admin_client: TestClient) -> None:
    response = admin_client.post("/api/users", json={"email": "newuser@example.com", "password": "short"})
    assert response.status_code == 422


def test_post_users_duplicate_email_conflict(admin_client: TestClient) -> None:
    response = admin_client.post("/api/users", json={"email": "admin@example.com", "password": "strongpass"})
    assert response.status_code == 409


def test_patch_deactivate_requires_auth(client: TestClient) -> None:
    response = client.patch("/api/users/some-id/deactivate")
    assert response.status_code == 401


def test_patch_deactivate_non_admin_gets_403(client: TestClient) -> None:
    backend_app.dependency_overrides[jwt_authentication] = override_user_auth
    try:
        response = client.patch("/api/users/some-id/deactivate")
    finally:
        backend_app.dependency_overrides.clear()
    assert response.status_code == 403


def test_patch_deactivate_self_returns_403(admin_client: TestClient) -> None:
    response = admin_client.patch("/api/users/admin-id/deactivate")
    assert response.status_code == 403


def test_patch_deactivate_returns_updated_user(admin_client: TestClient) -> None:
    response = admin_client.patch("/api/users/user-id/deactivate")
    assert response.status_code == 200
    data = response.json()
    assert data["is_active"] is False
    assert "roles" in data
    assert "password_hash" not in data


def test_patch_deactivate_nonexistent_user_returns_404(admin_client: TestClient) -> None:
    response = admin_client.patch("/api/users/nonexistent-id/deactivate")
    assert response.status_code == 404


def test_openapi_includes_user_management_paths(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    assert "/api/users" in schema["paths"]
    assert "/api/users/{id}/deactivate" in schema["paths"]
