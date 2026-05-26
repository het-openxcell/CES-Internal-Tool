import sqlalchemy
from sqlalchemy.orm import selectinload

from src.models.db.role import Role, UserRole
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

    async def find_by_username_with_roles(self, username: str) -> User | None:
        stmt = sqlalchemy.select(User).options(selectinload(User.roles)).where(User.username == username)
        result = await self.async_session.execute(stmt)
        return result.scalar_one_or_none()

    async def read_all_with_roles(self) -> list[User]:
        stmt = (
            sqlalchemy.select(User)
            .options(selectinload(User.roles))
            .order_by(User.created_at.asc())
        )
        result = await self.async_session.execute(stmt)
        return list(result.scalars().all())

    async def create_user(self, username: str, password_hash: str, is_active: bool = True) -> User:
        return await self.create(
            {"username": username, "password_hash": password_hash, "is_active": is_active},
            commit=False,
        )

    async def assign_role(self, user: User, role: Role) -> None:
        self.async_session.add(UserRole(user_id=user.id, role_id=role.id))
        await self.async_session.commit()

    async def deactivate(self, user: User) -> User:
        stmt = (
            sqlalchemy.update(User)
            .where(User.id == user.id)
            .values(
                is_active=False,
                updated_at=sqlalchemy.text("EXTRACT(EPOCH FROM now())::BIGINT"),
            )
        )
        await self.async_session.execute(stmt)
        await self.async_session.commit()
        return await self.read_user_with_roles(user.id)

    async def read_user_with_roles(self, user_id: str) -> User | None:
        stmt = sqlalchemy.select(User).options(selectinload(User.roles)).where(User.id == user_id)
        result = await self.async_session.execute(stmt)
        return result.scalar_one_or_none()
