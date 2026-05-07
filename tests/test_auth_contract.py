import asyncio
import time

from src.models.db.user import User
from src.models.schemas.auth import LoginRequest, LoginResponse
from src.securities.authorizations.jwt import jwt_generator
from src.securities.hashing.password import pwd_generator


def test_user_model_matches_users_table_contract() -> None:
    assert User.__tablename__ == "users"
    assert {"id", "username", "password_hash", "created_at", "updated_at"}.issubset(User.__table__.columns.keys())


def test_login_schema_matches_previous_contract() -> None:
    request = LoginRequest(username="ces.staff", password="correct-password")
    response = LoginResponse(token="token", expires_at=int(time.time()))

    assert request.model_dump() == {"username": "ces.staff", "password": "correct-password"}
    assert set(response.model_dump().keys()) == {"token", "expires_at"}


def test_password_generator_hashes_and_verifies_bcrypt() -> None:
    async def verify() -> None:
        password_hash = await pwd_generator.generate_hashed_password("correct-password")

        assert await pwd_generator.is_password_authenticated("correct-password", password_hash)
        assert not await pwd_generator.is_password_authenticated("wrong-password", password_hash)
        assert not await pwd_generator.is_password_authenticated("correct-password", "not-a-bcrypt-hash")

    asyncio.run(verify())


def test_jwt_generator_returns_token_and_epoch_expiry() -> None:
    user = User(
        id="11111111-1111-1111-1111-111111111111",
        username="ces.staff",
        password_hash="hash",
        created_at=int(time.time()),
        updated_at=int(time.time()),
    )

    token, expires_at = jwt_generator.generate_access_token(user)
    payload = jwt_generator.retrieve_details_from_token(token)

    assert isinstance(token, str)
    assert isinstance(expires_at, int)
    assert payload["user_id"] == "11111111-1111-1111-1111-111111111111"
