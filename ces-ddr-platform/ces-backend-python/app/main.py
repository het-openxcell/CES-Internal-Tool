from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.api.auth import AuthRouter
from app.api.health import HealthRouter
from app.auth.jwt import JWTManager
from app.auth.middleware import JWTAuthMiddleware, RequestLoggingMiddleware
from app.config import AppSettings
from app.db.pool import DatabasePool
from app.db.queries.users import UserRepository
from app.exceptions import ExceptionHandlers


class AppFactory:
    def __init__(self, settings: AppSettings | None = None, user_repository: UserRepository | None = None) -> None:
        self.settings = settings or AppSettings()
        self.user_repository = user_repository

    def create(self) -> FastAPI:
        app = FastAPI(title=self.settings.app_name)
        jwt_manager = JWTManager.from_settings(self.settings)
        user_repository = self.user_repository or UserRepository(DatabasePool(self.settings.postgres_dsn))
        app.add_middleware(
            JWTAuthMiddleware,
            jwt_manager=jwt_manager,
            public_paths={("GET", "/health"), ("POST", "/auth/login")},
        )
        app.add_middleware(
            RequestLoggingMiddleware,
            service="ces-backend-python",
            jwt_secret=self.settings.jwt_secret,
            postgres_password=self.settings.postgres_password,
        )
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[self.settings.cors_allowed_origin],
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type"],
        )
        app.include_router(HealthRouter().router)
        app.include_router(AuthRouter(user_repository=user_repository, jwt_manager=jwt_manager).router)
        ExceptionHandlers().register(app)
        return app


app = AppFactory().create()
