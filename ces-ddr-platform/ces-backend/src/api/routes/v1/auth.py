from fastapi import APIRouter, Depends, status

from src.api.dependencies.repository import get_repository
from src.models.schemas.auth import LoginRequest, LoginResponse
from src.repository.crud.user import UserCRUDRepository
from src.securities.authorizations.jwt import jwt_generator
from src.securities.hashing.password import pwd_generator
from src.utilities.exceptions.exceptions import InvalidCredentialsException

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def login(
    request: LoginRequest,
    user_repository: UserCRUDRepository = Depends(get_repository(UserCRUDRepository)),
) -> LoginResponse:
    user = await user_repository.find_by_username(request.username)

    password_hash = user.password_hash if user else pwd_generator.dummy_hash()

    is_authenticated = await pwd_generator.is_password_authenticated(request.password, password_hash)
    if user is None or not is_authenticated:
        raise InvalidCredentialsException("Invalid credentials")

    token, expires_at = jwt_generator.generate_access_token(user)
    return LoginResponse(token=token, expires_at=expires_at)
