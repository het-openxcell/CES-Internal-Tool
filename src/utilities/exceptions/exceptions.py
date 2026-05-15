from typing import Dict, Optional

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from src.models.schemas.response import MessageModel, ResponseModel as Response
from src.utilities.logging.logger import logger
import inspect


def get_call_hierarchy_from_stack() -> str:
    try:
        stack = inspect.stack()

        filtered_frames = []
        skip_patterns = [
            'exception_json_response',
            'handle_exception',
            'general_exception_handler',
            '__call__',
            'wrapper',
            'dispatch',
            'get_call_hierarchy_from_stack'
        ]

        for frame in stack:
            func_name = frame.function
            filename = frame.filename

            if any(pattern in func_name for pattern in skip_patterns):
                continue

            if any(pattern in filename for pattern in ['starlette', 'fastapi', 'uvicorn']):
                continue

            if 'src/' in filename:
                filtered_frames.append(func_name)

        if filtered_frames:
            seen = set()
            unique_frames = []
            for frame in reversed(filtered_frames):
                if frame not in seen:
                    unique_frames.append(frame)
                    seen.add(frame)

            return " -> ".join(unique_frames)

        return "unknown"

    except Exception as e:
        logger.debug(f"Error extracting call hierarchy: {e}")
        return "unknown"


async def exception_json_response(
    status_code: int,
    request: Request,
    detail: str,
    error: str = None,
    format_data: Optional[Dict[str, str]] = None,
    call_hierarchy: Optional[str] = None,
    **kwargs
):
    if call_hierarchy is None:
        call_hierarchy = get_call_hierarchy_from_stack()

    log_message = f"Handled Exception: Status={status_code}, Path={request.url.path}, Detail='{detail}', Error='{error}', Hierarchy='{call_hierarchy}'"

    if 400 <= status_code < 500:
        logger.warning(log_message)
    elif status_code >= 500:
        logger.error(log_message, exc_info=Exception(error) if error else None)
    else:
        logger.info(log_message)

    return JSONResponse(
        status_code=status_code,
        content=Response(
            success=False,
            error_code=status_code,
            message=MessageModel(
                title=error or "request_error",
                description=detail
            ),
            call_hierarchy=call_hierarchy
        ).model_dump(),
        headers=kwargs.get('headers', {})
    )

async def general_exception_handler(request: Request, exc: Exception):
    hierarchy = getattr(exc, '_call_hierarchy', None)
    if hierarchy is None:
        hierarchy = get_call_hierarchy_from_stack()

    return JSONResponse(
        status_code=500,
        content=Response(
            success=False,
            error_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=MessageModel(
                title="internal_server_error",
                description="An internal server error occurred"
            ),
            call_hierarchy=hierarchy
        ).model_dump(),
    )


class BaseTrackedException(Exception):

    def __init__(self, detail: str, format_data: dict = None):
        self.detail = detail
        self.format_data = format_data or {}
        self._call_hierarchy = get_call_hierarchy_from_stack()
        Exception.__init__(self, detail)

    def get_hierarchy(self) -> str:
        return self._call_hierarchy or "unknown"


class BadRequestException(BaseTrackedException, HTTPException):
    def __init__(self, detail: str = "bad_request", format_data: dict = None):
        BaseTrackedException.__init__(self, detail, format_data)
        HTTPException.__init__(self, status_code=400, detail=detail)


class EntityAlreadyExistsException(BaseTrackedException):
    def __init__(self, detail: str = "ENTITY_ALREADY_EXIST", format_data: dict = None):
        super().__init__(detail, format_data)


class EntityDoesNotExistException(Exception):
    def __init__(self, detail: str = "entity_does_not_exist", format_data: dict = None):
        self.detail = detail
        self.format_data = format_data or {}


class AuthorizationHeaderException(Exception):
    def __init__(self, detail: str = "authorization_failed"):
        self.detail = detail


class InvalidCredentialsException(Exception):
    def __init__(self, detail: str = "invalid_credentials", format_data: dict = None):
        self.detail = detail
        self.format_data = format_data or {}


class PasswordDoesNotMatchException(Exception):
    def __init__(self, detail: str = "password_does_not_match"):
        self.detail = detail


class SecurityException(BaseTrackedException):
    def __init__(self, detail: str = "security_error", format_data: dict = None):
        super().__init__(detail, format_data)


class EntityAlreadyExists(EntityAlreadyExistsException):
    pass


class EntityDoesNotExist(EntityDoesNotExistException):
    pass


async def bad_request_exception_handler(request: Request, exc: BadRequestException):
    return await exception_json_response(status.HTTP_400_BAD_REQUEST, request, exc.detail, str(exc), format_data=exc.format_data, call_hierarchy=exc.get_hierarchy())


async def entity_already_exists_exception_handler(request: Request, exc: EntityAlreadyExistsException):
    return await exception_json_response(status.HTTP_409_CONFLICT, request, exc.detail, "ENTITY_ALREADY_EXIST", format_data=exc.format_data, call_hierarchy=exc.get_hierarchy())


async def entity_does_not_exist_exception_handler(request: Request, exc: EntityDoesNotExistException):
    return await exception_json_response(status.HTTP_404_NOT_FOUND, request, exc.detail, str(exc), format_data=exc.format_data)


async def authorization_header_exception_handler(request: Request, exc: AuthorizationHeaderException):
    return await exception_json_response(status.HTTP_401_UNAUTHORIZED, request, exc.detail, "AUTH_TOKEN_NOT_PROVIDED", headers={"WWW-Authenticate": "Bearer"})


async def invalid_credentials_exception_handler(request: Request, exc: InvalidCredentialsException):
    return await exception_json_response(status.HTTP_401_UNAUTHORIZED, request, exc.detail, str(exc), format_data=exc.format_data)


async def security_exception_handler(request: Request, exc: SecurityException):
    return await exception_json_response(status.HTTP_403_FORBIDDEN, request, exc.detail, str(exc), format_data=exc.format_data, call_hierarchy=exc.get_hierarchy())
