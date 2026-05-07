from abc import ABC, abstractmethod
from typing import Dict, Type
from fastapi import Request, status
from .exceptions import exception_json_response


class ExceptionStrategy(ABC):
    
    @abstractmethod
    def get_status_code(self) -> int:
        pass
    
    @abstractmethod
    def get_error_type(self) -> str:
        pass
    
    @abstractmethod
    def get_headers(self) -> Dict[str, str]:
        pass
    
    async def handle_exception(self, request: Request, exc: Exception):
        # Try to get hierarchy from exception, otherwise it will be auto-captured
        hierarchy = getattr(exc, '_call_hierarchy', None)
        
        return await exception_json_response(
            status_code=self.get_status_code(),
            request=request,
            detail=exc.detail if hasattr(exc, 'detail') else str(exc),
            error=self.get_error_type(),
            format_data=getattr(exc, 'format_data', {}),
            call_hierarchy=hierarchy,
            headers=self.get_headers()
        )


class BadRequestStrategy(ExceptionStrategy):
    
    def get_status_code(self) -> int:
        return status.HTTP_400_BAD_REQUEST
    
    def get_error_type(self) -> str:
        return "BAD_REQUEST"
    
    def get_headers(self) -> Dict[str, str]:
        return {}


class ValidationStrategy(ExceptionStrategy):
    
    def get_status_code(self) -> int:
        return status.HTTP_400_BAD_REQUEST
    
    def get_error_type(self) -> str:
        return "VALIDATION_ERROR"
    
    def get_headers(self) -> Dict[str, str]:
        return {}


class NotFoundStrategy(ExceptionStrategy):
    
    def get_status_code(self) -> int:
        return status.HTTP_404_NOT_FOUND
    
    def get_error_type(self) -> str:
        return "NOT_FOUND"
    
    def get_headers(self) -> Dict[str, str]:
        return {}


class EntityAlreadyExistsStrategy(ExceptionStrategy):
    
    def get_status_code(self) -> int:
        return status.HTTP_409_CONFLICT
    
    def get_error_type(self) -> str:
        return "ENTITY_ALREADY_EXISTS"
    
    def get_headers(self) -> Dict[str, str]:
        return {}


class SecurityStrategy(ExceptionStrategy):
    
    def get_status_code(self) -> int:
        return status.HTTP_401_UNAUTHORIZED
    
    def get_error_type(self) -> str:
        return "SECURITY_ERROR"
    
    def get_headers(self) -> Dict[str, str]:
        return {"WWW-Authenticate": "Bearer"}


class InternalServerErrorStrategy(ExceptionStrategy):
    
    def get_status_code(self) -> int:
        return status.HTTP_500_INTERNAL_SERVER_ERROR
    
    def get_error_type(self) -> str:
        return "INTERNAL_SERVER_ERROR"
    
    def get_headers(self) -> Dict[str, str]:
        return {}


class UnauthorizedStrategy(ExceptionStrategy):
    
    def get_status_code(self) -> int:
        return status.HTTP_401_UNAUTHORIZED
    
    def get_error_type(self) -> str:
        return "UNAUTHORIZED"
    
    def get_headers(self) -> Dict[str, str]:
        return {"WWW-Authenticate": "Bearer"}


class TokenExpiredStrategy(ExceptionStrategy):
    
    def get_status_code(self) -> int:
        return status.HTTP_401_UNAUTHORIZED
    
    def get_error_type(self) -> str:
        return "TOKEN_EXPIRED"
    
    def get_headers(self) -> Dict[str, str]:
        return {"WWW-Authenticate": "Bearer"}


class ForbiddenStrategy(ExceptionStrategy):
    
    def get_status_code(self) -> int:
        return status.HTTP_403_FORBIDDEN
    
    def get_error_type(self) -> str:
        return "FORBIDDEN"
    
    def get_headers(self) -> Dict[str, str]:
        return {}


class DataIntegrityStrategy(ExceptionStrategy):
    
    def get_status_code(self) -> int:
        return status.HTTP_400_BAD_REQUEST
    
    def get_error_type(self) -> str:
        return "DATA_INTEGRITY_ERROR"
    
    def get_headers(self) -> Dict[str, str]:
        return {}


class ExternalAPIStrategy(ExceptionStrategy):
    
    def get_status_code(self) -> int:
        return status.HTTP_502_BAD_GATEWAY
    
    def get_error_type(self) -> str:
        return "EXTERNAL_API_ERROR"
    
    def get_headers(self) -> Dict[str, str]:
        return {}


class DatabaseConnectionStrategy(ExceptionStrategy):
    
    def get_status_code(self) -> int:
        return status.HTTP_503_SERVICE_UNAVAILABLE
    
    def get_error_type(self) -> str:
        return "DATABASE_CONNECTION_ERROR"
    
    def get_headers(self) -> Dict[str, str]:
        return {}


class InsufficientResourcesStrategy(ExceptionStrategy):
    
    def get_status_code(self) -> int:
        return status.HTTP_402_PAYMENT_REQUIRED
    
    def get_error_type(self) -> str:
        return "INSUFFICIENT_RESOURCES"
    
    def get_headers(self) -> Dict[str, str]:
        return {}


class DefaultStrategy(ExceptionStrategy):
    
    def get_status_code(self) -> int:
        return status.HTTP_500_INTERNAL_SERVER_ERROR
    
    def get_error_type(self) -> str:
        return "UNKNOWN_ERROR"
    
    def get_headers(self) -> Dict[str, str]:
        return {} 