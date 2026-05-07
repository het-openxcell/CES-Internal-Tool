import json
import logging
import re
import time
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.auth.errors import ErrorResponses
from app.auth.jwt import JWTManager


class JWTAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: object, jwt_manager: JWTManager, public_paths: set[tuple[str, str]]) -> None:
        super().__init__(app)
        self.jwt_manager = jwt_manager
        self.public_paths = public_paths

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if (request.method, request.url.path) in self.public_paths:
            return await call_next(request)

        authorization = request.headers.get("Authorization", "")
        if not authorization.startswith("Bearer "):
            return JSONResponse(status_code=401, content=ErrorResponses.unauthorized("Authentication required"))

        try:
            payload = self.jwt_manager.validate(authorization.removeprefix("Bearer ").strip())
        except ValueError:
            return JSONResponse(status_code=401, content=ErrorResponses.unauthorized("Authentication required"))

        request.state.user_id = payload["user_id"]
        return await call_next(request)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: object, service: str, jwt_secret: str, postgres_password: str) -> None:
        super().__init__(app)
        self.service = service
        self.jwt_secret = jwt_secret
        self.postgres_password = postgres_password
        self.logger = logging.getLogger(service)
        self.logger.setLevel(logging.INFO)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = str(uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        self.logger.info(
            json.dumps(
                {
                    "timestamp": int(time.time()),
                    "level": "info",
                    "service": self.service,
                    "request_id": request_id,
                    "message": self.sanitize(f"{request.method} {request.url.path}"),
                }
            )
        )
        return response

    def sanitize(self, value: str) -> str:
        value = re.sub(r"Authorization|JWT_SECRET|POSTGRES_PASSWORD", "[redacted]", value)
        for secret in [self.jwt_secret, self.postgres_password]:
            if secret:
                value = value.replace(secret, "[redacted]")
        return value
