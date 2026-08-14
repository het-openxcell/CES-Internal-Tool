from typing import Optional

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordBearer
from fastapi.security.utils import get_authorization_scheme_param
from sqlalchemy.ext.asyncio import AsyncSession as SQLAlchemyAsyncSession

from src.api.dependencies.session import get_async_session
from src.models.db.user import User
from src.repository.crud.user import UserCRUDRepository
from src.securities.authorizations.jwt import jwt_generator
from src.utilities.exceptions.exceptions import AuthorizationHeaderException, SecurityException


class CustomHTTPBearer(HTTPBearer):
    async def __call__(
        self, request: Request
    ) -> Optional[HTTPAuthorizationCredentials]:
        authorization = request.headers.get("Authorization")
        scheme, credentials = get_authorization_scheme_param(authorization)
        if not (authorization and scheme and credentials):
            if self.auto_error:
                raise AuthorizationHeaderException("sign_in_required")
            else:
                return None
        if scheme.lower() != "bearer":
            if self.auto_error:
                raise AuthorizationHeaderException("session_expired_or_closed")
            else:
                return None
        return HTTPAuthorizationCredentials(scheme=scheme, credentials=credentials)


security = CustomHTTPBearer()


class StreamQueryTokenAuthentication:
    async def __call__(
        self,
        request: Request,
        async_session: SQLAlchemyAsyncSession = Depends(get_async_session),
    ) -> User:
        token = request.query_params.get("access_token")
        if token is None:
            raise AuthorizationHeaderException("sign_in_required")

        return await authenticate_token(request=request, token=token, async_session=async_session)


stream_query_token_authentication = StreamQueryTokenAuthentication()


class CustomOAuth2PasswordBearer(OAuth2PasswordBearer):
    def __init__(self, token_url: str, param_name: str = "Authorization"):
        super().__init__(token_url)
        self.param_name = param_name

    async def __call__(self, request: Request) -> str:
        authorization: str = request.headers.get(self.param_name)

        if authorization is None:
            raise AuthorizationHeaderException("AUTH_TOKEN_MISSING")

        if authorization.startswith("Bearer "):
            token = authorization[7:]
        else:
            raise AuthorizationHeaderException(detail="AUTH_TOKEN_MISSING")

        return token


async def get_current_user(user_id: str, async_session: SQLAlchemyAsyncSession) -> User | None:
    user = await UserCRUDRepository(async_session=async_session).read_user_with_roles(user_id=user_id)
    if user is not None and not user.is_active:
        return None
    return user


async def authenticate_token(request: Request, token: str, async_session: SQLAlchemyAsyncSession) -> User:
    try:
        token_data = jwt_generator.retrieve_details_from_token(token)
    except SecurityException as security_error:
        raise AuthorizationHeaderException(detail=str(security_error))

    current_user = await get_current_user(user_id=token_data["user_id"], async_session=async_session)
    if not current_user:
        raise AuthorizationHeaderException(detail="sign_in_required")

    request.state.user = current_user
    request.state.token_data = token_data

    return current_user


async def jwt_authentication(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    async_session: SQLAlchemyAsyncSession = Depends(get_async_session),
) -> User:
    return await authenticate_token(request=request, token=credentials.credentials, async_session=async_session)
