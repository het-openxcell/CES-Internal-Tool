import re

from pydantic import field_validator

from src.models.schemas.base import BaseSchemaModel
from src.services.occurrence.classify import VALID_SECTIONS

_YYYYMMDD = re.compile(r"^\d{8}$")


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
        if v is not None and not _YYYYMMDD.match(v):
            raise ValueError("date must be YYYYMMDD (8 digits)")
        return v


class OccurrenceInDB(OccurrenceInCreate):
    id: str
    created_at: int
    updated_at: int
