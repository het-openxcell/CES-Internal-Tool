from decouple import config
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BackendBaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class AppSettings(BackendBaseSettings):
    app_name: str = Field(default_factory=lambda: config("APP_NAME", default="CES DDR Python Backend"))
    app_env: str = Field(default_factory=lambda: config("APP_ENV", default="local"))
    python_backend_host: str = Field(default_factory=lambda: config("PYTHON_BACKEND_HOST", default="0.0.0.0"))
    python_backend_port: int = Field(default_factory=lambda: config("PYTHON_BACKEND_PORT", default=8000, cast=int))
    postgres_dsn: str = Field(
        default_factory=lambda: config(
            "POSTGRES_DSN",
            default="postgresql://ces:change-me-local-only@localhost:5432/ces_ddr",
        )
    )
    postgres_password: str = Field(default_factory=lambda: config("POSTGRES_PASSWORD", default=""))
    qdrant_host: str = Field(default_factory=lambda: config("QDRANT_HOST", default="localhost"))
    qdrant_port: int = Field(default_factory=lambda: config("QDRANT_PORT", default=6333, cast=int))
    jwt_secret: str = Field(default_factory=lambda: config("JWT_SECRET", default=""))
