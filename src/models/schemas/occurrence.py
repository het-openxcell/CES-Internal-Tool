import re

from pydantic import ConfigDict, field_validator

from src.constants.occurrence import VALID_SECTIONS
from src.models.schemas.base import BaseSchemaModel


class OccurrenceInCreate(BaseSchemaModel):
    ddr_id: str
    ddr_date_id: str
    well_name: str | None = None
    surface_location: str | None = None
    type: str
    section: str | None = None
    mmd: float | None = None
    density: float | None = None
    notes: str | None = None
    date: str | None = None
    page_number: int | None = None
    is_exported: bool = False

    @field_validator("section")
    @classmethod
    def validate_section(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_SECTIONS:
            raise ValueError(f"section must be one of {sorted(VALID_SECTIONS)} or None")
        return v

    @field_validator("date")
    @classmethod
    def validate_date_format(cls, v: str | None) -> str | None:
        if v is not None and not re.compile(r"^\d{8}$").match(v):
            raise ValueError("date must be YYYYMMDD (8 digits)")
        return v


class OccurrenceInResponse(BaseSchemaModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    ddr_id: str
    ddr_date_id: str
    well_name: str | None = None
    surface_location: str | None = None
    type: str
    section: str | None = None
    mmd: float | None = None
    density: float | None = None
    notes: str | None = None
    date: str | None = None
    page_number: int | None = None
    is_exported: bool


class HistoryOccurrenceInResponse(OccurrenceInResponse):
    operator: str | None = None
    area: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    from_mmd: float | None = None
    to_mmd: float | None = None
