import asyncio
import json
import logging
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient
import pytest
from jose import jwt

from app.auth.jwt import JWTManager
from app.auth.password import PasswordVerifier
from app.config import AppSettings
from app.main import AppFactory
from app.models.user import User


async def protected_test() -> dict[str, str]:
    return {"status": "ok"}


class FakeUserRepository:
    def __init__(self, user: User | None) -> None:
        self.user = user

    async def find_by_username(self, username: str) -> User | None:
        return self.user


def test_shared_auth_fixtures_keep_contract_shape() -> None:
    fixture_root = Path(__file__).parents[1] / "fixtures" / "auth"

    assert set(json.loads((fixture_root / "login-success-response.json").read_text()).keys()) == {"token", "expires_at"}
    assert set(json.loads((fixture_root / "login-invalid-credentials-response.json").read_text()).keys()) == {
        "error",
        "code",
        "details",
    }
    assert set(json.loads((fixture_root / "authentication-required-response.json").read_text()).keys()) == {
        "error",
        "code",
        "details",
    }


def test_shared_jwt_fixture_validates_with_python_manager() -> None:
    fixture = shared_user_fixture()

    claims = JWTManager(fixture["jwt_secret"], timedelta(hours=8)).validate(fixture["valid_token"])

    assert claims["user_id"] == fixture["id"]
    assert asyncio.run(PasswordVerifier().verify(fixture["password"], fixture["password_hash"]))


def test_password_verifier_uses_bcrypt_hash() -> None:
    password_hash = asyncio.run(PasswordVerifier().hash("correct-password"))

    assert asyncio.run(PasswordVerifier().verify("correct-password", password_hash))
    assert not asyncio.run(PasswordVerifier().verify("wrong-password", password_hash))


def test_login_returns_signed_jwt() -> None:
    password_hash = PasswordVerifier().hash_sync("correct-password")
    client = TestClient(
        AppFactory(
            settings=AppSettings(jwt_secret="test-jwt-secret"),
            user_repository=FakeUserRepository(
                User(
                    id="11111111-1111-1111-1111-111111111111",
                    username="ces.staff",
                    password_hash=password_hash,
                )
            ),
        ).create()
    )

    response = client.post("/auth/login", json={"username": "ces.staff", "password": "correct-password"})

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"token", "expires_at"}
    claims = JWTManager("test-jwt-secret", timedelta(hours=8)).validate(body["token"])
    assert claims["user_id"] == "11111111-1111-1111-1111-111111111111"
    assert isinstance(body["expires_at"], int)
    assert int(time.time()) + 7 * 60 * 60 + 59 * 60 <= body["expires_at"] <= int(time.time()) + 8 * 60 * 60 + 60


def test_cors_preflight_allows_configured_frontend_origin() -> None:
    client = TestClient(AppFactory(settings=AppSettings(jwt_secret="test-jwt-secret")).create())

    response = client.options(
        "/auth/login",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "Content-Type" in response.headers["access-control-allow-headers"]


def test_login_wrong_username_and_password_return_same_unauthorized_body() -> None:
    password_hash = PasswordVerifier().hash_sync("correct-password")
    client = TestClient(
        AppFactory(
            settings=AppSettings(jwt_secret="test-jwt-secret"),
            user_repository=FakeUserRepository(
                User(
                    id="11111111-1111-1111-1111-111111111111",
                    username="ces.staff",
                    password_hash=password_hash,
                )
            ),
        ).create()
    )
    missing_user_client = TestClient(
        AppFactory(settings=AppSettings(jwt_secret="test-jwt-secret"), user_repository=FakeUserRepository(None)).create()
    )

    wrong_password = client.post("/auth/login", json={"username": "ces.staff", "password": "wrong-password"})
    missing_user = missing_user_client.post("/auth/login", json={"username": "missing", "password": "wrong-password"})

    expected = {"error": "Invalid credentials", "code": "UNAUTHORIZED", "details": {}}
    assert wrong_password.status_code == 401
    assert missing_user.status_code == 401
    assert wrong_password.json() == expected
    assert missing_user.json() == expected


def test_jwt_middleware_rejects_missing_malformed_bad_signature_and_expired_tokens() -> None:
    app = AppFactory(settings=AppSettings(jwt_secret="test-jwt-secret")).create()
    app.add_api_route("/protected-test", protected_test, methods=["GET"])
    client = TestClient(app)
    expired = JWTManager("test-jwt-secret", timedelta(hours=-1)).generate("11111111-1111-1111-1111-111111111111")[0]
    bad_signature = JWTManager("other-secret", timedelta(hours=8)).generate("11111111-1111-1111-1111-111111111111")[0]
    missing_exp = jwt.encode({"user_id": "11111111-1111-1111-1111-111111111111"}, "test-jwt-secret", algorithm="HS256")
    bad_user_id = jwt.encode({"user_id": {"id": "nested"}, "exp": datetime.now(UTC) + timedelta(hours=8)}, "test-jwt-secret", algorithm="HS256")

    cases = [
        {},
        {"Authorization": "Bearer no"},
        {"Authorization": f"Bearer {bad_signature}"},
        {"Authorization": f"Bearer {expired}"},
        {"Authorization": f"Bearer {missing_exp}"},
        {"Authorization": f"Bearer {bad_user_id}"},
    ]

    for headers in cases:
        response = client.get("/protected-test", headers=headers)
        assert response.status_code == 401
        assert response.json() == {"error": "Authentication required", "code": "UNAUTHORIZED", "details": {}}


def test_request_logging_includes_request_id_and_excludes_secrets(caplog) -> None:
    caplog.set_level(logging.INFO, logger="ces-backend")
    client = TestClient(
        AppFactory(
            settings=AppSettings(jwt_secret="super-secret-value", postgres_password="postgres-secret-value"),
        ).create()
    )

    response = client.get(
        "/health/super-secret-value/postgres-secret-value/JWT_SECRET/POSTGRES_PASSWORD/Authorization",
        headers={"Authorization": "Bearer should-not-log"},
    )

    assert response.status_code == 401
    log_text = caplog.text
    for required in ["timestamp", "level", "service", "request_id", "message"]:
        assert required in log_text
    for secret in [
        "Authorization",
        "should-not-log",
        "super-secret-value",
        "postgres-secret-value",
        "JWT_SECRET",
        "POSTGRES_PASSWORD",
    ]:
        assert secret not in log_text


def test_jwt_manager_rejects_missing_placeholder_and_no_exp_tokens() -> None:
    for secret in ["", "placeholder-jwt-secret"]:
        with pytest.raises(ValueError):
            JWTManager(secret, timedelta(hours=8))

    token = jwt.encode({"user_id": "11111111-1111-1111-1111-111111111111"}, "test-jwt-secret", algorithm="HS256")

    with pytest.raises(ValueError):
        JWTManager("test-jwt-secret", timedelta(hours=8)).validate(token)


def test_corrupt_password_hash_returns_false() -> None:
    assert not asyncio.run(PasswordVerifier().verify("correct-password", "not-a-bcrypt-hash"))


def shared_user_fixture() -> dict[str, str]:
    fixture_root = Path(__file__).parents[1] / "fixtures" / "auth"
    return json.loads((fixture_root / "shared-user.json").read_text())
