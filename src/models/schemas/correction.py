from pydantic import field_validator

from src.models.schemas.base import BaseSchemaModel


class CorrectionInCreate(BaseSchemaModel):
    occurrence_id: str
    field_name: str
    original_value: str
    corrected_value: str
    reason: str

    @field_validator("field_name", "original_value", "corrected_value", "reason")
    @classmethod
    def must_be_non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be empty")
        return v


class CorrectionInResponse(BaseSchemaModel):
    id: str
    occurrence_id: str
    ddr_id: str
    field_name: str
    original_value: str
    corrected_value: str
    reason: str
    user_id: str
    created_at: int
