from typing import Type, Dict, Optional
from fastapi import Request, FastAPI
from fastapi.responses import JSONResponse
from .factory import exception_strategy_factory, ExceptionStrategyFactory
from .exceptions import (
    BadRequestException,
    ValidationException,
    NotFoundException,
    DataNotFoundError,
    EntityAlreadyExistsException,
    SecurityException,
    InternalServerErrorException,
    UnauthorizedException,
    TokenExpiredException,
    DataIntegrityError,
    ExternalAPIException,
    DatabaseConnectionError,
    InsufficientResourcesException,
    VoiceIDCountException,
    PasswordDoesNotMatchException,
    EntityDoesNotExistException,
    CannotDowngradeYearlyToMonthlyException,
    AuthorizationHeaderException,
    TokenNotProvidedException,
    AccountIsNotActiveException,
    OTPExpiredException,
    UserNotFoundException,
    UserAlreadyExistsException,
    InvalidCredentialsException,
    ExternalAPIError,
    HeyGenAPIError,
    AzureAPIError,
    general_exception_handler
)
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from jose import ExpiredSignatureError
from starlette.exceptions import HTTPException as StarletteHTTPException
from src.utilities.logging.logger import logger


class ExceptionHandlerRegistry:
    
    def __init__(self, strategy_factory: ExceptionStrategyFactory = None):
        self._strategy_factory = strategy_factory or exception_strategy_factory
        self._registered_handlers: Dict[Type[Exception], bool] = {}
    
    async def handle_exception(self, request: Request, exc: Exception) -> JSONResponse:
        try:
            # Get the appropriate strategy for this exception type
            strategy = self._strategy_factory.get_strategy(type(exc))
            
            # Use the strategy to handle the exception
            response = await strategy.handle_exception(request, exc)
            
            # Log the successful handling
            hierarchy = getattr(exc, '_call_hierarchy', None)
            if hierarchy is None:
                from .exceptions import get_call_hierarchy_from_stack
                hierarchy = get_call_hierarchy_from_stack()
            logger.info(f"Exception handled by {strategy.__class__.__name__}: {type(exc).__name__} - Hierarchy: {hierarchy}")
            
            return response
            
        except Exception as handler_error:
            # If the handler itself fails, fall back to a basic error response
            logger.error(f"Exception handler failed: {handler_error}", exc_info=True)
            
            # Use the general exception handler as ultimate fallback
            return await general_exception_handler(request, exc)
    
    def register_with_app(self, app: FastAPI):
        # Register handlers for all known exception types
        exception_types = [
            BadRequestException,
            ValidationException,
            NotFoundException,
            DataNotFoundError,
            EntityAlreadyExistsException,
            SecurityException,
            InternalServerErrorException,
            UnauthorizedException,
            TokenExpiredException,
            DataIntegrityError,
            ExternalAPIException,
            DatabaseConnectionError,
            InsufficientResourcesException,
            VoiceIDCountException,
            PasswordDoesNotMatchException,
            EntityDoesNotExistException,
            CannotDowngradeYearlyToMonthlyException,
            AuthorizationHeaderException,
            TokenNotProvidedException,
            AccountIsNotActiveException,
            OTPExpiredException,
            UserNotFoundException,
            UserAlreadyExistsException,
            InvalidCredentialsException,
            ExternalAPIError,
            HeyGenAPIError,
            AzureAPIError,
            HTTPException,
            StarletteHTTPException,
            RequestValidationError,
            ExpiredSignatureError,
            ValueError,
        ]
        
        # Register the unified handler for each exception type
        for exc_type in exception_types:
            if exc_type not in self._registered_handlers:
                app.add_exception_handler(exc_type, self.handle_exception)
                self._registered_handlers[exc_type] = True
                logger.info(f"Registered exception handler for {exc_type.__name__}")
        
        # Register the general exception handler as the ultimate fallback
        app.add_exception_handler(Exception, self.handle_exception)
        logger.info("Registered general exception handler")
    
    def get_strategy_factory(self) -> ExceptionStrategyFactory:
        return self._strategy_factory
    
    def get_registered_handlers(self) -> Dict[Type[Exception], bool]:
        return self._registered_handlers.copy()


# Global registry instance
exception_registry = ExceptionHandlerRegistry()


def setup_exception_handlers(app: FastAPI):
    exception_registry.register_with_app(app)
    logger.info("Exception handling system initialized successfully")


def get_exception_registry() -> ExceptionHandlerRegistry:
    return exception_registry 