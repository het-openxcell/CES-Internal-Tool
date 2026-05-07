from typing import Any, Dict

from fastapi import Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError

from src.securities.authorizations.jwt import jwt_generator
from src.utilities.exceptions.exceptions import AuthorizationHeaderException, SecurityException
from src.utilities.logging.logger import logger

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def verify_token(token: str, request: Request) -> Dict[str, Any]:
    try:
        token_data = jwt_generator.retrieve_details_from_token(token)
        return token_data

    except SecurityException as security_error:
        logger.warning(f"Security exception during token verification: {str(security_error)}")
        raise AuthorizationHeaderException(detail=str(security_error)) from security_error
    except JWTError as jwt_error:
        logger.warning(f"JWT error during token verification: {str(jwt_error)}")
        raise AuthorizationHeaderException(detail="Could not validate credentials") from jwt_error
