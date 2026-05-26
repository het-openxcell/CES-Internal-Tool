from fastapi import APIRouter, Depends, status
from sqlalchemy.exc import IntegrityError

from src.api.dependencies.repository import get_repository
from src.models.db.user import User
from src.models.schemas.user import CreateUserRequest, UserResponse
from src.repository.crud.role import RoleCRUDRepository
from src.repository.crud.user import UserCRUDRepository
from src.securities.authorizations.jwt_authentication import jwt_authentication
from src.securities.authorizations.rbac import admin_only
from src.securities.hashing.password import pwd_generator
from src.utilities.exceptions.exceptions import EntityDoesNotExist, ForbiddenException, UsernameConflictException

router = APIRouter(prefix="/users", tags=["Users"])


def _user_response(user) -> UserResponse:
    return UserResponse(
        id=user.id,
        username=user.username,
        is_active=user.is_active,
        roles=[r.name for r in user.roles],
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.get("/", response_model=list[UserResponse], status_code=status.HTTP_200_OK, dependencies=[Depends(admin_only)])
async def list_users(
    user_repository: UserCRUDRepository = Depends(get_repository(UserCRUDRepository)),
) -> list[UserResponse]:
    users = await user_repository.read_all_with_roles()
    return [_user_response(u) for u in users]


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(admin_only)])
async def create_user(
    body: CreateUserRequest,
    user_repository: UserCRUDRepository = Depends(get_repository(UserCRUDRepository)),
    role_repository: RoleCRUDRepository = Depends(get_repository(RoleCRUDRepository)),
) -> UserResponse:
    existing = await user_repository.find_by_username(body.username)
    if existing is not None:
        raise UsernameConflictException()

    user_role = await role_repository.find_by_name("USER")
    if user_role is None:
        raise EntityDoesNotExist("USER role not seeded")

    password_hash = await pwd_generator.generate_hashed_password(body.password)
    try:
        new_user = await user_repository.create_user(username=body.username, password_hash=password_hash)
        await user_repository.assign_role(new_user, user_role)
    except IntegrityError:
        raise UsernameConflictException() from None

    user_with_roles = await user_repository.read_user_with_roles(new_user.id)
    return _user_response(user_with_roles)


@router.patch(
    "/{id}/deactivate",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(admin_only)],
)
async def deactivate_user(
    id: str,
    current_user: User = Depends(jwt_authentication),
    user_repository: UserCRUDRepository = Depends(get_repository(UserCRUDRepository)),
) -> UserResponse:
    if id == str(current_user.id):
        raise ForbiddenException("cannot_deactivate_self")

    user = await user_repository.read_user_with_roles(id)
    if user is None:
        raise EntityDoesNotExist(f"User {id} not found")

    updated = await user_repository.deactivate(user)
    return _user_response(updated)
