from pydantic import Field

from src.models.schemas.base import BaseSchemaModel


class UserResponse(BaseSchemaModel):
    id: str
    email: str
    is_active: bool
    roles: list[str]
    created_at: int
    updated_at: int


class CreateUserRequest(BaseSchemaModel):
    email: str
    password: str = Field(..., min_length=8)


class UpdateUserRequest(BaseSchemaModel):
    email: str
