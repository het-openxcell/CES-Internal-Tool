from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.manager import settings
from src.repository.crud.role import RoleCRUDRepository
from src.repository.crud.user import UserCRUDRepository
from src.securities.hashing.password import pwd_generator


class SeedService:
    @staticmethod
    async def seed_roles_and_admin(async_session: AsyncSession) -> None:
        role_repo = RoleCRUDRepository(async_session=async_session)
        user_repo = UserCRUDRepository(async_session=async_session)

        admin_role = await role_repo.find_by_name("ADMIN")
        if admin_role is None:
            try:
                admin_role = await role_repo.create_role("ADMIN", "Full system access")
            except IntegrityError:
                await async_session.rollback()
                admin_role = await role_repo.find_by_name("ADMIN")

        user_role = await role_repo.find_by_name("USER")
        if user_role is None:
            try:
                await role_repo.create_role("USER", "Standard access")
            except IntegrityError:
                await async_session.rollback()

        existing_admin = await user_repo.find_by_username(settings.ADMIN_USERNAME)
        if existing_admin is None:
            try:
                password_hash = await pwd_generator.generate_hashed_password(settings.ADMIN_PASSWORD)
                admin_user = await user_repo.create_user(
                    username=settings.ADMIN_USERNAME,
                    password_hash=password_hash,
                )
                await user_repo.assign_role(admin_user, admin_role)
            except IntegrityError:
                await async_session.rollback()
