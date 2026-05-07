# Exception handling system with automatic call hierarchy tracking
from .exceptions import *
from .strategies import ExceptionStrategy
from .factory import ExceptionStrategyFactory, exception_strategy_factory
from .registry import ExceptionHandlerRegistry, exception_registry, setup_exception_handlers

__all__ = [
    # Core exceptions
    "BaseTrackedException",
    "BadRequestException",
    "ValidationException",
    "NotFoundException",
    "EntityAlreadyExistsException",
    "SecurityException",
    "InternalServerErrorException",
    "UnauthorizedException",
    "TokenExpiredException",
    
    # Strategy pattern
    "ExceptionStrategy",
    "ExceptionStrategyFactory",
    "exception_strategy_factory",
    
    # Registry
    "ExceptionHandlerRegistry",
    "exception_registry",
    "setup_exception_handlers",
    
    # Response models (imported from models.schemas.response)
    # "ExceptionResponseModel",
    
    # Utility functions
    "exception_json_response",
    "general_exception_handler",
    "get_call_hierarchy_from_stack",
]
