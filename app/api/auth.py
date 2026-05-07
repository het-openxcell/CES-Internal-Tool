from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.auth.errors import ErrorResponses
from app.auth.jwt import JWTManager
from app.auth.password import PasswordVerifier
from app.db.queries.users import UserRepository


class LoginRequest(BaseModel):
    username: str
    password: str


class AuthRouter:
    def __init__(self, user_repository: UserRepository, jwt_manager: JWTManager) -> None:
        self.router = APIRouter(prefix="/auth")
        self.user_repository = user_repository
        self.jwt_manager = jwt_manager
        self.password_verifier = PasswordVerifier()
        self.router.add_api_route("/login", self.login, methods=["POST"])

    async def login(self, request: LoginRequest) -> JSONResponse:
        user = await self.user_repository.find_by_username(request.username)
        password_hash = user.password_hash if user else self.password_verifier.dummy_hash()

        if not await self.password_verifier.verify(request.password, password_hash) or user is None:
            return JSONResponse(status_code=401, content=ErrorResponses.unauthorized("Invalid credentials"))

        token, expires_at = self.jwt_manager.generate(user.id)
        return JSONResponse(
            status_code=200,
            content={"token": token, "expires_at": expires_at},
        )
