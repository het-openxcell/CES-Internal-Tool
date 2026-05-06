from fastapi import FastAPI

from app.api.health import HealthRouter
from app.config import AppSettings
from app.exceptions import ExceptionHandlers


class AppFactory:
    def __init__(self, settings: AppSettings | None = None) -> None:
        self.settings = settings or AppSettings()

    def create(self) -> FastAPI:
        app = FastAPI(title=self.settings.app_name)
        app.include_router(HealthRouter().router)
        ExceptionHandlers().register(app)
        return app


app = AppFactory().create()
