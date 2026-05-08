import logging
import pathlib

import decouple
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR: pathlib.Path = pathlib.Path(__file__).parent.parent.parent.parent.resolve()
config = decouple.AutoConfig(search_path=str(ROOT_DIR))


class BackendBaseSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    TITLE: str = "Backend API"
    VERSION: str = "0.1.0"
    TIMEZONE: str = "UTC"
    DESCRIPTION: str | None = None
    DEBUG: bool = config("DEBUG", cast=bool, default=False)

    SERVER_HOST: str = config("BACKEND_SERVER_HOST", default="0.0.0.0", cast=str)
    SERVER_PORT: int = config("BACKEND_SERVER_PORT", default=8000, cast=int)
    SERVER_WORKERS: int = config("BACKEND_SERVER_WORKERS", default=1, cast=int)
    API_PREFIX: str = "/api"
    DOCS_URL: str = "/docs"
    OPENAPI_URL: str = "/openapi.json"
    REDOC_URL: str = "/redoc"
    OPENAPI_PREFIX: str = ""

    DB_POSTGRES_HOST: str = config("POSTGRES_HOST", default="localhost", cast=str)
    DB_MAX_POOL_CON: int = config("DB_MAX_POOL_CON", default=10, cast=int)
    DB_POSTGRES_NAME: str = config("POSTGRES_DB", default="ces_ddr", cast=str)
    DB_POSTGRES_PASSWORD: str = config("POSTGRES_PASSWORD", default="change-me-local-only", cast=str)
    DB_POOL_SIZE: int = config("DB_POOL_SIZE", default=5, cast=int)
    DB_POOL_OVERFLOW: int = config("DB_POOL_OVERFLOW", default=10, cast=int)
    DB_POSTGRES_PORT: int = config("POSTGRES_PORT", default=5432, cast=int)
    DB_POSTGRES_SCHEMA: str = config("POSTGRES_SCHEMA", default="postgresql", cast=str)
    DB_TIMEOUT: int = config("DB_TIMEOUT", default=30, cast=int)
    DB_POSTGRES_USERNAME: str = config("POSTGRES_USERNAME", default="ces", cast=str)

    IS_DB_ECHO_LOG: bool = config("IS_DB_ECHO_LOG", default=False, cast=bool)
    IS_DB_FORCE_ROLLBACK: bool = config("IS_DB_FORCE_ROLLBACK", default=False, cast=bool)
    IS_DB_EXPIRE_ON_COMMIT: bool = config("IS_DB_EXPIRE_ON_COMMIT", default=False, cast=bool)

    API_TOKEN: str = config("API_TOKEN", default="", cast=str)
    AUTH_TOKEN: str = config("AUTH_TOKEN", default="", cast=str)
    JWT_TOKEN_PREFIX: str = config("JWT_TOKEN_PREFIX", default="Bearer", cast=str)
    JWT_SECRET_KEY: str = config("JWT_SECRET_KEY", default="placeholder-jwt-secret", cast=str)
    JWT_SUBJECT: str = config("JWT_SUBJECT", default="access", cast=str)
    JWT_MIN: int = config("JWT_MIN", default=60, cast=int)
    JWT_HOUR: int = config("JWT_HOUR", default=8, cast=int)
    JWT_DAY: int = config("JWT_DAY", default=1, cast=int)
    JWT_ACCESS_TOKEN_EXPIRATION_TIME: int = JWT_MIN * JWT_HOUR * JWT_DAY

    JWT_FORGOT_PASSWORD_SUBJECT: str = config("JWT_FORGOT_PASSWORD_SUBJECT", default="password-reset", cast=str)
    JWT_ALGORITHM: str = config("JWT_ALGORITHM", default="HS256", cast=str)

    IS_ALLOWED_CREDENTIALS: bool = config("IS_ALLOWED_CREDENTIALS", default=True, cast=bool)
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://0.0.0.0:3000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://localhost:5173",
        "http://0.0.0.0:5173",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ]
    ALLOWED_METHODS: list[str] = ["*"]
    ALLOWED_HEADERS: list[str] = ["*"]

    LOGGING_LEVEL: int = logging.INFO
    LOGGERS: tuple[str, str] = ("uvicorn.asgi", "uvicorn.access")

    LOG_LEVEL: str = config("LOG_LEVEL", default="INFO", cast=str)

    PERFORMANCE_THRESHOLD_MS: float = config("PERFORMANCE_THRESHOLD_MS", default=1000.0, cast=float)
    UPLOAD_DIR: str = config(
        "UPLOAD_DIR",
        default="/home/het/Desktop/Canadian%20Energy%20Service%20Internal%20Tool/extras/uploads/",
        cast=str,
    )

    ASYNC_LOGGING: bool = config("ASYNC_LOGGING", default=True, cast=bool)
    BACKTRACE_ENABLED: bool = config("BACKTRACE_ENABLED", default=True, cast=bool)
    DIAGNOSE_ENABLED: bool = config("DIAGNOSE_ENABLED", default=True, cast=bool)
    COLORIZE_CONSOLE: bool = config("COLORIZE_CONSOLE", default=True, cast=bool)

    HASHING_ALGORITHM_LAYER_1: str = config("HASHING_ALGORITHM_LAYER_1", default="bcrypt", cast=str)
    HASHING_ALGORITHM_LAYER_2: str = config("HASHING_ALGORITHM_LAYER_2", default="sha256", cast=str)
    HASHING_SALT: str = config("HASHING_SALT", default="change-me-local-only", cast=str)

    KEY_HEX: str = config("KEY_HEX", cast=str, default="")

    GEMINI_API_KEY: str = config("GEMINI_API_KEY", cast=str, default="")
    GEMINI_MODEL: str = config("GEMINI_MODEL", cast=str, default="gemini-2.5-flash-lite")
    GEMINI_EXTRACTION_MAX_CONCURRENT: int = config("GEMINI_EXTRACTION_MAX_CONCURRENT", cast=int, default=3)
    GEMINI_EXTRACTION_MAX_RETRIES: int = config("GEMINI_EXTRACTION_MAX_RETRIES", cast=int, default=3)
    GEMINI_FLASH_LITE_INPUT_COST_PER_1M_TOKENS: str = config(
        "GEMINI_FLASH_LITE_INPUT_COST_PER_1M_TOKENS",
        cast=str,
        default="0.10",
    )
    GEMINI_FLASH_LITE_OUTPUT_COST_PER_1M_TOKENS: str = config(
        "GEMINI_FLASH_LITE_OUTPUT_COST_PER_1M_TOKENS",
        cast=str,
        default="0.40",
    )
    GEMINI_EMBEDDING_MODEL: str = config("GEMINI_EMBEDDING_MODEL", cast=str, default="gemini-embedding-2")
    GEMINI_EMBEDDING_DIMENSION: int = config("GEMINI_EMBEDDING_DIMENSION", cast=int, default=3072)

    QDRANT_URL: str = config("QDRANT_URL", cast=str, default="http://localhost:6333")
    QDRANT_API_KEY: SecretStr | None = config("QDRANT_API_KEY", cast=str, default=None)
    QDRANT_COLLECTION_DDR_TIME_LOGS: str = config(
        "QDRANT_COLLECTION_DDR_TIME_LOGS",
        cast=str,
        default="ddr_time_logs",
    )

    @property
    def set_backend_app_attributes(self) -> dict[str, str | bool | None]:
        return {
            "title": self.TITLE,
            "version": self.VERSION,
            "debug": self.DEBUG,
            "description": self.DESCRIPTION,
            "docs_url": self.DOCS_URL,
            "openapi_url": self.OPENAPI_URL,
            "redoc_url": self.REDOC_URL,
            "openapi_prefix": self.OPENAPI_PREFIX,
            "api_prefix": self.API_PREFIX,
        }
