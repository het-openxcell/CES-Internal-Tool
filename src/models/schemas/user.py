from pydantic import Field

from src.models.schemas.base import BaseSchemaModel


class UserResponse(BaseSchemaModel):
    id: str
    username: str
    is_active: bool
    roles: list[str]
    created_at: int
    updated_at: int


class CreateUserRequest(BaseSchemaModel):
    username: str
    password: str = Field(..., min_length=8)
