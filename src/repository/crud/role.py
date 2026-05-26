import sqlalchemy

from src.models.db.role import Role
from src.repository.crud.base import BaseCRUDRepository


class RoleCRUDRepository(BaseCRUDRepository[Role]):
    model = Role

    async def find_by_name(self, name: str) -> Role | None:
        stmt = sqlalchemy.select(Role).where(Role.name == name)
        result = await self.async_session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_role(self, name: str, description: str | None = None) -> Role:
        return await self.create({"name": name, "description": description})
