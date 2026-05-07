from src.models.schemas.base import BaseSchemaModel


class LoginRequest(BaseSchemaModel):
    username: str
    password: str


class LoginResponse(BaseSchemaModel):
    token: str
    expires_at: int
