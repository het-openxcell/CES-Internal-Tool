class ErrorResponses:
    @staticmethod
    def unauthorized(message: str) -> dict[str, object]:
        return {"error": message, "code": "UNAUTHORIZED", "details": {}}
