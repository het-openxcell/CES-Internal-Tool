import sqlalchemy
from sqlalchemy.orm import selectinload

from src.models.db.role import Role, UserRole
from src.models.db.user import User
from src.repository.crud.base import BaseCRUDRepository
from src.utilities.exceptions import EntityDoesNotExist


class UserCRUDRepository(BaseCRUDRepository[User]):
    model = User

    async def read_user_by_email(self, email: str) -> User:
        stmt = sqlalchemy.select(User).where(User.email == email)
        query = await self.async_session.execute(statement=stmt)
        user = query.scalar_one_or_none()
        if user is None:
            raise EntityDoesNotExist(f"User with email `{email}` does not exist!")
        return user

    async def find_by_email(self, email: str) -> User | None:
        stmt = sqlalchemy.select(User).where(User.email == email)
        query = await self.async_session.execute(statement=stmt)
        return query.scalar_one_or_none()

    async def find_by_email_with_roles(self, email: str) -> User | None:
        stmt = sqlalchemy.select(User).options(selectinload(User.roles)).where(User.email == email)
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

    async def create_user(self, email: str, password_hash: str, is_active: bool = True) -> User:
        return await self.create(
            {"email": email, "password_hash": password_hash, "is_active": is_active},
            commit=False,
        )

    async def assign_role(self, user: User, role: Role) -> None:
        self.async_session.add(UserRole(user_id=user.id, role_id=role.id))
        await self.async_session.commit()

    async def update_email(self, user: User, email: str) -> User:
        stmt = (
            sqlalchemy.update(User)
            .where(User.id == user.id)
            .values(
                email=email,
                updated_at=sqlalchemy.text("EXTRACT(EPOCH FROM now())::BIGINT"),
            )
        )
        await self.async_session.execute(stmt)
        await self.async_session.commit()
        return await self.read_user_with_roles(user.id)

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
