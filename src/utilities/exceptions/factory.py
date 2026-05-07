from typing import Type, Dict, Optional
from .strategies import (
    ExceptionStrategy,
    BadRequestStrategy,
    ValidationStrategy,
    NotFoundStrategy,
    EntityAlreadyExistsStrategy,
    SecurityStrategy,
    InternalServerErrorStrategy,
    UnauthorizedStrategy,
    TokenExpiredStrategy,
    ForbiddenStrategy,
    DataIntegrityStrategy,
    ExternalAPIStrategy,
    DatabaseConnectionStrategy,
    InsufficientResourcesStrategy,
    DefaultStrategy
)
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
    AzureAPIError
)
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from jose import ExpiredSignatureError


class ExceptionStrategyFactory:
    
    def __init__(self):
        self._strategies: Dict[Type[Exception], ExceptionStrategy] = {
            # Core HTTP exceptions
            BadRequestException: BadRequestStrategy(),
            ValidationException: ValidationStrategy(),
            NotFoundException: NotFoundStrategy(),
            DataNotFoundError: NotFoundStrategy(),
            
            # Entity exceptions
            EntityAlreadyExistsException: EntityAlreadyExistsStrategy(),
            
            # Security exceptions
            SecurityException: SecurityStrategy(),
            UnauthorizedException: UnauthorizedStrategy(),
            TokenExpiredException: TokenExpiredStrategy(),
            ExpiredSignatureError: TokenExpiredStrategy(),
            AuthorizationHeaderException: UnauthorizedStrategy(),
            TokenNotProvidedException: UnauthorizedStrategy(),
            InvalidCredentialsException: UnauthorizedStrategy(),
            
            # Server errors
            InternalServerErrorException: InternalServerErrorStrategy(),
            DatabaseConnectionError: DatabaseConnectionStrategy(),
            ExternalAPIException: ExternalAPIStrategy(),
            ExternalAPIError: ExternalAPIStrategy(),
            HeyGenAPIError: ExternalAPIStrategy(),
            AzureAPIError: ExternalAPIStrategy(),
            
            # Business logic exceptions
            DataIntegrityError: DataIntegrityStrategy(),
            InsufficientResourcesException: InsufficientResourcesStrategy(),
            VoiceIDCountException: BadRequestStrategy(),
            PasswordDoesNotMatchException: BadRequestStrategy(),
            EntityDoesNotExistException: NotFoundStrategy(),
            CannotDowngradeYearlyToMonthlyException: BadRequestStrategy(),
            AccountIsNotActiveException: ForbiddenStrategy(),
            OTPExpiredException: UnauthorizedStrategy(),
            UserNotFoundException: NotFoundStrategy(),
            UserAlreadyExistsException: EntityAlreadyExistsStrategy(),
            
            # FastAPI exceptions
            HTTPException: BadRequestStrategy(),
            RequestValidationError: ValidationStrategy(),
            ValueError: BadRequestStrategy(),
        }
        
        # Default strategy for unregistered exceptions
        self._default_strategy = DefaultStrategy()
    
    def get_strategy(self, exception_type: Type[Exception]) -> ExceptionStrategy:
        # Try exact match first
        if exception_type in self._strategies:
            return self._strategies[exception_type]
        
        # Try to find a strategy for a parent class
        for registered_type, strategy in self._strategies.items():
            if issubclass(exception_type, registered_type):
                return strategy
        
        # Return default strategy if no match found
        return self._default_strategy
    
    def register_strategy(self, exception_type: Type[Exception], strategy: ExceptionStrategy):
        self._strategies[exception_type] = strategy
    
    def unregister_strategy(self, exception_type: Type[Exception]):
        if exception_type in self._strategies:
            del self._strategies[exception_type]
    
    def get_registered_types(self) -> Dict[Type[Exception], ExceptionStrategy]:
        return self._strategies.copy()
    
    def set_default_strategy(self, strategy: ExceptionStrategy):
        self._default_strategy = strategy


# Global factory instance
exception_strategy_factory = ExceptionStrategyFactory() 