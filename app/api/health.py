from fastapi import APIRouter


class HealthRouter:
    def __init__(self) -> None:
        self.router = APIRouter()
        self.router.add_api_route("/health", self.read, methods=["GET"])

    async def read(self) -> dict[str, str]:
        return {"status": "ok"}
