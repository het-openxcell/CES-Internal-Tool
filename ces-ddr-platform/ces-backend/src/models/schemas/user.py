import uuid

import pydantic

from src.models.schemas.base import BaseSchemaModel


class UserInCreate(BaseSchemaModel):
    username: str
    email: pydantic.EmailStr
    password: str


class UserInUpdate(BaseSchemaModel):
    username: str | None = None
    email: str | None = None
    password: str | None = None


class UserInLogin(BaseSchemaModel):
    username: str
    password: str


class UserWithToken(BaseSchemaModel):
    token: str
    username: str
    email: pydantic.EmailStr
    is_verified: bool
    is_active: bool
    is_logged_in: bool
    created_at: int
    updated_at: int | None


class UserInResponse(BaseSchemaModel):
    id: uuid.UUID
    authorized_user: UserWithToken