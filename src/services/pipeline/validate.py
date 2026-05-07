import json
from dataclasses import dataclass, field
from typing import Any

import pydantic

from src.models.schemas.ddr import DDRExtractionPayload


@dataclass
class ValidationResult:
    raw_text: str
    raw_json: dict[str, Any] | None = None
    final_json: dict[str, Any] | None = None
    errors: list[dict[str, Any]] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return self.final_json is not None and not self.errors


class DDRExtractionValidator:
    payload_model = DDRExtractionPayload

    def validate(self, raw_text: str) -> ValidationResult:
        result = ValidationResult(raw_text=raw_text)
        try:
            parsed = json.loads(raw_text) if raw_text else None
        except json.JSONDecodeError as exc:
            result.errors = [{"type": "json_decode_error", "msg": str(exc), "loc": []}]
            return result

        if not isinstance(parsed, dict):
            result.errors = [{"type": "type_error", "msg": "expected_object", "loc": []}]
            return result

        result.raw_json = parsed

        try:
            payload = self.payload_model.model_validate(parsed)
        except pydantic.ValidationError as exc:
            result.errors = self._serialize_errors(exc)
            return result

        result.final_json = payload.model_dump(mode="json")
        return result

    def _serialize_errors(self, exc: pydantic.ValidationError) -> list[dict[str, Any]]:
        return [
            {
                "type": err.get("type"),
                "msg": err.get("msg"),
                "loc": [str(item) for item in err.get("loc", ())],
            }
            for err in exc.errors()
        ]
