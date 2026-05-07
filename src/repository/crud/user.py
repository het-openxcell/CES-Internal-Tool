import time
import typing

import sqlalchemy

from src.models.db.user import User
from src.models.schemas.auth import LoginRequest
from src.repository.crud.base import BaseCRUDRepository
from src.securities.hashing.password import pwd_generator
from src.utilities.exceptions import EntityDoesNotExist
from src.utilities.exceptions.exceptions import PasswordDoesNotMatchException as PasswordDoesNotMatch


class UserCRUDRepository(BaseCRUDRepository[User]):
    model = User

    async def create_user(self, username: str, password: str) -> User:
        return await self.create(
            {
                "username": username,
                "password_hash": await pwd_generator.generate_hashed_password(password),
                "created_at": int(time.time()),
                "updated_at": int(time.time()),
            }
        )

    async def read_users(self) -> typing.Sequence[User]:
        return await self.read_many()

    async def read_user_by_id(self, user_id: str) -> User:
        user = await self.read_by_id(user_id)
        if user is None:
            raise EntityDoesNotExist(f"User with id `{user_id}` does not exist!")
        return user

    async def read_user_by_username(self, username: str) -> User:
        stmt = sqlalchemy.select(User).where(User.username == username)
        query = await self.async_session.execute(statement=stmt)
        user = query.scalar_one_or_none()
        if user is None:
            raise EntityDoesNotExist(f"User with username `{username}` does not exist!")
        return user

    async def read_user_by_password_authentication(self, user_login: LoginRequest) -> User:
        db_user = await self.read_user_by_username(user_login.username)
        is_authenticated = await pwd_generator.is_password_authenticated(
            password=user_login.password,
            hashed_password=db_user.password_hash,
        )
        if not is_authenticated:
            raise PasswordDoesNotMatch("Password does not match!")
        return db_user

    async def find_by_username(self, username: str) -> User | None:
        stmt = sqlalchemy.select(User).where(User.username == username)
        query = await self.async_session.execute(statement=stmt)
        return query.scalar_one_or_none()

    async def update_user_password(self, user: User, password: str) -> User:
        return await self.update(
            user,
            {
                "password_hash": await pwd_generator.generate_hashed_password(password),
                "updated_at": int(time.time()),
            },
        )
