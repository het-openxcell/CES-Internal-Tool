from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt

from app.config import AppSettings


class JWTManager:
    ALGORITHM = "HS256"
    INSECURE_PLACEHOLDER_SECRET = "placeholder-jwt-secret"

    def __init__(self, secret: str, lifetime: timedelta) -> None:
        if not secret.strip() or secret == self.INSECURE_PLACEHOLDER_SECRET:
            raise ValueError("JWT secret is required")
        self.secret = secret
        self.lifetime = lifetime

    @classmethod
    def from_settings(cls, settings: AppSettings) -> "JWTManager":
        return cls(settings.jwt_secret, timedelta(hours=8))

    def generate(self, user_id: str) -> tuple[str, int]:
        expires_at = datetime.now(UTC) + self.lifetime
        token = jwt.encode({"user_id": user_id, "exp": expires_at}, self.secret, algorithm=self.ALGORITHM)
        return token, int(expires_at.timestamp())

    def validate(self, token: str) -> dict[str, object]:
        try:
            payload = jwt.decode(token, self.secret, algorithms=[self.ALGORITHM])
        except JWTError as exc:
            raise ValueError("Invalid token") from exc
        if not isinstance(payload.get("user_id"), str) or not payload["user_id"] or "exp" not in payload:
            raise ValueError("Invalid token")
        return payload
