import datetime
import uuid
from typing import Any

from jose import JWTError
from jose import jwt as jose_jwt

from src.config.manager import settings
from src.models.db.user import User
from src.models.schemas.jwt import JWTUser, JWToken
from src.utilities.exceptions import EntityDoesNotExist
from src.utilities.exceptions.exceptions import SecurityException
from src.utilities.logging.logger import logger


class JWTGenerator:
    def _generate_jwt_token(
        self,
        *,
        jwt_data: dict[str, Any],
        expires_delta: datetime.timedelta,
        jti: str,
        subject: str,
    ) -> str:
        expire = datetime.datetime.now(datetime.UTC) + expires_delta
        to_encode = jwt_data | JWToken(exp=expire, sub=subject, jti=jti).model_dump()
        return jose_jwt.encode(to_encode, key=settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    def generate_access_token(self, user: User) -> tuple[str, int]:
        if not user:
            raise EntityDoesNotExist("Cannot generate JWT token without User entity!")

        expiration_seconds = settings.JWT_ACCESS_TOKEN_EXPIRATION_TIME * 60
        expires_delta = datetime.timedelta(seconds=expiration_seconds)
        token_data = JWTUser(user_id=str(user.id), username=user.username).model_dump()
        token = self._generate_jwt_token(
            jwt_data=token_data,
            expires_delta=expires_delta,
            jti=str(uuid.uuid4()),
            subject=settings.JWT_SUBJECT,
        )
        return token, int((datetime.datetime.now(datetime.UTC) + expires_delta).timestamp())

    def retrieve_details_from_token(self, token: str) -> dict[str, Any]:
        try:
            payload = jose_jwt.decode(
                token=token,
                key=settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )
            user_id = payload.get("user_id")
            if not isinstance(user_id, str) or not user_id:
                raise SecurityException("Invalid JWT payload structure")
            if not payload.get("jti"):
                raise SecurityException("Missing JWT ID")
            return {
                "user_id": user_id,
                "jti": payload["jti"],
                "token_type": "access",
                "raw_payload": payload,
            }
        except JWTError as token_decode_error:
            logger.error(f"JWT decode error: {str(token_decode_error)}")
            raise SecurityException("Unable to decode JWT Token") from token_decode_error


def get_jwt_generator() -> JWTGenerator:
    return JWTGenerator()


jwt_generator: JWTGenerator = get_jwt_generator()
