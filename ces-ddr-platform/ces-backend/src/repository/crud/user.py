import sqlalchemy

from src.models.db.user import User
from src.repository.crud.base import BaseCRUDRepository
from src.utilities.exceptions import EntityDoesNotExist


class UserCRUDRepository(BaseCRUDRepository[User]):
    model = User

    async def read_user_by_username(self, username: str) -> User:
        stmt = sqlalchemy.select(User).where(User.username == username)
        query = await self.async_session.execute(statement=stmt)
        user = query.scalar_one_or_none()
        if user is None:
            raise EntityDoesNotExist(f"User with username `{username}` does not exist!")
        return user

    async def find_by_username(self, username: str) -> User | None:
        stmt = sqlalchemy.select(User).where(User.username == username)
        query = await self.async_session.execute(statement=stmt)
        return query.scalar_one_or_none()
