from typing import Dict, Optional
from fastapi import Request, HTTPException, status, WebSocket
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from jose import ExpiredSignatureError
from src.models.schemas.response import MessageModel, ResponseModel as Response
from src.utilities.logging.logger import logger
from starlette.exceptions import HTTPException as StarletteHTTPException
import inspect
import traceback


def get_call_hierarchy_from_stack() -> str:
    try:
        # Get the current stack frames
        stack = inspect.stack()
        
        # Filter out frames we don't want (exception handling internals)
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
            
            # Skip internal exception handling functions
            if any(pattern in func_name for pattern in skip_patterns):
                continue
                
            # Skip internal FastAPI/Starlette frames
            if any(pattern in filename for pattern in ['starlette', 'fastapi', 'uvicorn']):
                continue
                
            # Only include functions from our source code
            if 'src/' in filename:
                filtered_frames.append(func_name)
        
        # Reverse to get the call order (deepest first)
        if filtered_frames:
            # Remove duplicates while preserving order
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
    # Automatically get call hierarchy if not provided
    if call_hierarchy is None:
        call_hierarchy = get_call_hierarchy_from_stack()
    
    # Enhanced logging with hierarchy
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
            error_code=123,
            message=MessageModel(
                title="title",
                description=detail
            ),
            error=error,
            call_hierarchy=call_hierarchy
        ).model_dump(),
        headers=kwargs.get('headers', {})
    )

async def general_exception_handler(request: Request, exc: Exception):
    # Try to get hierarchy from exception, otherwise get from stack
    hierarchy = getattr(exc, '_call_hierarchy', None)
    if hierarchy is None:
        hierarchy = get_call_hierarchy_from_stack()
    
    return JSONResponse(
        status_code=500,
        content=Response(
            status=False,
            message="An internal server error occurred",
            error=str(exc),
            call_hierarchy=hierarchy
        ).model_dump(),
    )


class BaseTrackedException(Exception):
    
    def __init__(self, detail: str, format_data: dict = None):
        self.detail = detail
        self.format_data = format_data or {}
        # Automatically capture call hierarchy when exception is created
        self._call_hierarchy = get_call_hierarchy_from_stack()
        super().__init__(detail)
    
    def set_hierarchy(self, hierarchy: str):
        self._call_hierarchy = hierarchy
    
    def get_hierarchy(self) -> str:
        return self._call_hierarchy or "unknown"

class BadRequestException(BaseTrackedException, HTTPException):
    def __init__(self, detail: str = "bad_request", format_data: dict = None):
        BaseTrackedException.__init__(self, detail, format_data)
        HTTPException.__init__(self, status_code=400, detail=detail)

class ValidationException(BadRequestException):
    def __init__(self, detail: str = "validation_failed", format_data: dict = None):
        super().__init__(detail, format_data)

class NotFoundException(BaseTrackedException):
    def __init__(self, detail: str = "results_not_found", format_data: dict = None):
        super().__init__(detail, format_data)

class DataNotFoundError(NotFoundException):
    def __init__(self, detail: str = "data_not_found", format_data: dict = None):
        super().__init__(detail, format_data)

class InternalServerErrorException(Exception):
    def __init__(self, detail: str = "internal_server_error"):
        self.detail = detail

class DatabaseConnectionError(InternalServerErrorException):
    def __init__(self, detail: str = "database_connection_error"):
        self.detail = detail

class DataIntegrityError(BadRequestException):
    def __init__(self, detail: str = "data_integrity_error", format_data: dict = None):
        super().__init__(detail, format_data)

class ExternalAPIException(InternalServerErrorException):
    def __init__(self, detail: str, format_data: dict = None):
        self.detail = detail
        self.format_data = format_data or {}

class ExternalAPIError(Exception):
    def __init__(self, service: str, detail: str):
        self.service = service
        self.detail = detail
        super().__init__(f"{service}_api_error")

class HeyGenAPIError(ExternalAPIError):
    def __init__(self, detail: str):
        super().__init__("HeyGen", "heygen_api_error")

class AzureAPIError(ExternalAPIError):
    def __init__(self, detail: str):
        super().__init__("Azure", "azure_api_error")

class EntityAlreadyExistsException(BaseTrackedException):
    def __init__(self, detail: str = "ENTITY_ALREADY_EXIST", format_data: dict = None):
        super().__init__(detail, format_data)

class VoiceIDCountException(Exception):
    def __init__(self, detail: str, format_data: dict = None):
        self.detail = detail
        self.format_data = format_data or {}

class PasswordDoesNotMatchException(Exception):
    def __init__(self, detail: str = "password_does_not_match"):
        self.detail = detail

class EntityDoesNotExistException(Exception):
    def __init__(self, detail: str = "entity_does_not_exist", format_data: dict = None):
        self.detail = detail
        self.format_data = format_data or {}

class CannotDowngradeYearlyToMonthlyException(Exception):
    def __init__(self, detail: str = "cannot_downgrade_yearly_to_monthly", format_data: dict = None):
        self.detail = detail
        self.format_data = format_data or {}

class AuthorizationHeaderException(Exception):
    def __init__(self, detail: str = "authorization_failed"):
        self.detail = detail

class TokenNotProvidedException(Exception):
    def __init__(self, detail: str = "auth_token_not_provided"):
        self.detail = detail

class AccountIsNotActiveException(Exception):
    def __init__(self, detail: str = "account_not_active"):
        self.detail = detail

class OTPExpiredException(Exception):
    def __init__(self, detail: str = "otp_expired"):
        self.detail = detail

class TokenExpiredException(Exception):
    def __init__(self, detail="Token Expired"):
        self.detail = detail
        super().__init__(self.detail)

class UnauthorizedException(Exception):
    def __init__(self, detail="Unauthorized Exception"):
        self.detail = detail
        super().__init__(self.detail)

class InsufficientResourcesException(Exception):
    def __init__(self, detail: str = "insufficient_credits", format_data: dict = None):
        self.detail = detail
        self.format_data = format_data or {}

# Missing exception classes referenced in main.py
class UserNotFoundException(Exception):
    def __init__(self, detail: str = "user_not_found", format_data: dict = None):
        self.detail = detail
        self.format_data = format_data or {}

class UserAlreadyExistsException(Exception):
    def __init__(self, detail: str = "user_already_exists", format_data: dict = None):
        self.detail = detail
        self.format_data = format_data or {}

class InvalidCredentialsException(Exception):
    def __init__(self, detail: str = "invalid_credentials", format_data: dict = None):
        self.detail = detail
        self.format_data = format_data or {}

class SecurityException(BaseTrackedException):
    def __init__(self, detail: str = "security_error", format_data: dict = None):
        super().__init__(detail, format_data)

# Aliases for backward compatibility with database exceptions
class EntityAlreadyExists(EntityAlreadyExistsException):
    pass

class EntityDoesNotExist(EntityDoesNotExistException):
    pass

async def handle_websocket_exceptions(e: Exception, websocket: WebSocket):
    logger.error(f"WebSocket error: {str(e)}")
    await websocket.close()

async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return await exception_json_response(exc.status_code, request, exc.detail, str(exc))

async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    if errors:
        error_detail = errors[0]
        field_path = " -> ".join(str(loc) for loc in error_detail.get("loc", []))
        error_msg = f"validation_error"
        return await exception_json_response(status.HTTP_422_UNPROCESSABLE_ENTITY, request, error_msg, f"Validation error for field: {field_path}")
    return await exception_json_response(status.HTTP_422_UNPROCESSABLE_ENTITY, request, "validation_error", "Validation error")

async def fastapi_http_exception_handler(request: Request, exc: HTTPException):
    return await exception_json_response(exc.status_code, request, exc.detail, str(exc))

async def bad_request_exception_handler(request: Request, exc: BadRequestException):
    return await exception_json_response(status.HTTP_400_BAD_REQUEST, request, exc.detail, str(exc), format_data=exc.format_data, call_hierarchy=exc.get_hierarchy())

async def validation_exception_handler(request: Request, exc: ValidationException):
    return await exception_json_response(status.HTTP_422_UNPROCESSABLE_ENTITY, request, exc.detail, str(exc), format_data=exc.format_data, call_hierarchy=exc.get_hierarchy())

async def not_found_exception_handler(request: Request, exc: NotFoundException):
    return await exception_json_response(status.HTTP_404_NOT_FOUND, request, exc.detail, str(exc), format_data=exc.format_data, call_hierarchy=exc.get_hierarchy())

async def data_not_found_error_handler(request: Request, exc: DataNotFoundError):
    return await exception_json_response(status.HTTP_404_NOT_FOUND, request, exc.detail, str(exc), format_data=exc.format_data, call_hierarchy=exc.get_hierarchy())

async def internal_server_error_handler(request: Request, exc: InternalServerErrorException):
    return await exception_json_response(status.HTTP_500_INTERNAL_SERVER_ERROR, request, exc.detail, str(exc))

async def database_connection_error_handler(request: Request, exc: DatabaseConnectionError):
    return await exception_json_response(status.HTTP_500_INTERNAL_SERVER_ERROR, request, exc.detail, str(exc))

async def data_integrity_error_handler(request: Request, exc: DataIntegrityError):
    return await exception_json_response(status.HTTP_409_CONFLICT, request, exc.detail, str(exc), format_data=exc.format_data, call_hierarchy=exc.get_hierarchy())

async def external_api_exception_handler(request: Request, exc: ExternalAPIException):
    return await exception_json_response(status.HTTP_502_BAD_GATEWAY, request, exc.detail, "EXTERNAL_API_ERROR", format_data=exc.format_data)

async def entity_already_exists_exception_handler(request: Request, exc: EntityAlreadyExistsException):
    return await exception_json_response(status.HTTP_409_CONFLICT, request, exc.detail, "ENTITY_ALREADY_EXIST", format_data=exc.format_data, call_hierarchy=exc.get_hierarchy())

async def cannot_downgrade_yearly_to_monthly_exception_handler(request: Request, exc: CannotDowngradeYearlyToMonthlyException):
    return await exception_json_response(status.HTTP_400_BAD_REQUEST, request, exc.detail, str(exc), format_data=exc.format_data)

async def password_does_not_match_exception_handler(request: Request, exc: PasswordDoesNotMatchException):
    return await exception_json_response(status.HTTP_400_BAD_REQUEST, request, exc.detail, str(exc))

async def entity_does_not_exist_exception_handler(request: Request, exc: EntityDoesNotExistException):
    return await exception_json_response(status.HTTP_404_NOT_FOUND, request, exc.detail, str(exc), format_data=exc.format_data)

async def authorization_header_exception_handler(request: Request, exc: AuthorizationHeaderException):
    return await exception_json_response(status.HTTP_401_UNAUTHORIZED, request, exc.detail, "AUTH_TOKEN_NOT_PROVIDED", headers={"WWW-Authenticate": "Bearer"})

async def token_not_provided_exception_handler(request: Request, exc: TokenNotProvidedException):
    return await exception_json_response(status.HTTP_403_FORBIDDEN, request, exc.detail, str(exc))

async def value_error_handler(request: Request, exc: ValueError):
    return await exception_json_response(status.HTTP_400_BAD_REQUEST, request, str(exc), "ValueError")

async def account_is_not_active_exception_handler(request: Request, exc: AccountIsNotActiveException):
    return await exception_json_response(status.HTTP_406_NOT_ACCEPTABLE, request, exc.detail, str(exc))

async def heygen_api_error_handler(request: Request, exc: HeyGenAPIError):
    return await exception_json_response(status.HTTP_502_BAD_GATEWAY, request, exc.detail, str(exc))

async def azure_api_error_handler(request: Request, exc: AzureAPIError):
    return await exception_json_response(status.HTTP_502_BAD_GATEWAY, request, exc.detail, str(exc))

async def external_api_error_handler(request: Request, exc: ExternalAPIError):
    return await exception_json_response(status.HTTP_502_BAD_GATEWAY, request, exc.detail, str(exc))

async def otp_expired_exception_handler(request: Request, exc: OTPExpiredException):
    return await exception_json_response(status.HTTP_410_GONE, request, exc.detail, str(exc))

async def token_expired_exception_handler(request: Request, exc: TokenExpiredException):
    return await exception_json_response(status.HTTP_203_NON_AUTHORITATIVE_INFORMATION, request, exc.detail, str(exc))

async def expired_signature_error_handler(request: Request, exc: ExpiredSignatureError):
    return await exception_json_response(status.HTTP_401_UNAUTHORIZED, request, detail="token_expired", error=str(exc))

async def unauthorized_error_handler(request: Request, exc: UnauthorizedException):
    return await exception_json_response(status.HTTP_403_FORBIDDEN, request, detail="not_to_access_this", error=str(exc))

async def insufficient_resources_exception_handler(request: Request, exc: InsufficientResourcesException):
    return await exception_json_response(status.HTTP_402_PAYMENT_REQUIRED, request, exc.detail, str(exc), format_data=exc.format_data)

async def voice_id_count_exception_handler(request: Request, exc: VoiceIDCountException):
    return await exception_json_response(status.HTTP_400_BAD_REQUEST, request, exc.detail, str(exc), format_data=exc.format_data)

# New exception handlers for the missing exceptions
async def user_not_found_exception_handler(request: Request, exc: UserNotFoundException):
    return await exception_json_response(status.HTTP_404_NOT_FOUND, request, exc.detail, str(exc), format_data=exc.format_data)

async def user_already_exists_exception_handler(request: Request, exc: UserAlreadyExistsException):
    return await exception_json_response(status.HTTP_409_CONFLICT, request, exc.detail, str(exc), format_data=exc.format_data)

async def invalid_credentials_exception_handler(request: Request, exc: InvalidCredentialsException):
    return await exception_json_response(status.HTTP_401_UNAUTHORIZED, request, exc.detail, str(exc), format_data=exc.format_data)

async def security_exception_handler(request: Request, exc: SecurityException):
    return await exception_json_response(status.HTTP_403_FORBIDDEN, request, exc.detail, str(exc), format_data=exc.format_data, call_hierarchy=exc.get_hierarchy())