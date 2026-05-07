from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class ExceptionHandlers:
    def register(self, app: FastAPI) -> None:
        app.add_exception_handler(Exception, self.unhandled)

    async def unhandled(self, request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})
