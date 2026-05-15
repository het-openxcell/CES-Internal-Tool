from decimal import Decimal
from typing import Any

import pydantic
from pydantic import ConfigDict

from src.models.schemas.base import BaseSchemaModel


class DDRStatus:
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETE = "complete"
    FAILED = "failed"

    @classmethod
    def values(cls) -> tuple[str, ...]:
        return (cls.QUEUED, cls.PROCESSING, cls.COMPLETE, cls.FAILED)

    @classmethod
    def validate(cls, value: str) -> str:
        if value not in cls.values():
            raise ValueError("Invalid DDR status")
        return value


class DDRDateStatus:
    QUEUED = "queued"
    SUCCESS = "success"
    WARNING = "warning"
    FAILED = "failed"

    @classmethod
    def values(cls) -> tuple[str, ...]:
        return (cls.QUEUED, cls.SUCCESS, cls.WARNING, cls.FAILED)

    @classmethod
    def validate(cls, value: str) -> str:
        if value not in cls.values():
            raise ValueError("Invalid DDR date status")
        return value


class DDRBase(BaseSchemaModel):
    file_path: str
    status: str = DDRStatus.QUEUED
    well_name: str | None = None
    surface_location: str | None = None
    operator: str | None = None
    area: str | None = None

    @pydantic.field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        return DDRStatus.validate(value)


class DDRInCreate(DDRBase):
    pass


class DDRStatusUpdate(BaseSchemaModel):
    status: str

    @pydantic.field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        return DDRStatus.validate(value)


class DDRInResponse(DDRBase):
    id: str
    created_at: int
    updated_at: int


class DDRUploadResponse(BaseSchemaModel):
    id: str
    status: str

    @pydantic.field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        return DDRStatus.validate(value)


class DDRReprocessDatesRequest(BaseSchemaModel):
    dates: list[str] | str | None = None

    def selected_dates(self) -> list[str] | None:
        if self.dates is None or self.dates == "all":
            return None
        if isinstance(self.dates, list):
            return [str(date) for date in self.dates]
        return None


class DDRReprocessAcceptedResponse(BaseSchemaModel):
    status: str
    mode: str
    dates: list[str] | None = None


class DDRReprocessOccurrencesResponse(BaseSchemaModel):
    status: str
    mode: str
    total_occurrences: int | None = None
    error: str | None = None


class DDRListItemResponse(BaseSchemaModel):
    id: str
    file_path: str
    status: str
    well_name: str | None = None
    surface_location: str | None = None
    created_at: int
    uploaded_by_username: str | None = None

    @pydantic.field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        return DDRStatus.validate(value)


class DDRDateBase(BaseSchemaModel):
    ddr_id: str
    date: str
    status: str = DDRDateStatus.QUEUED
    raw_response: dict[str, Any] | None = None
    final_json: dict[str, Any] | None = None
    error_log: dict[str, Any] | None = None
    source_page_numbers: list[int] | None = None

    @pydantic.field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        return DDRDateStatus.validate(value)


class DDRDateInCreate(DDRDateBase):
    pass


class DDRDateStatusUpdate(BaseSchemaModel):
    status: str

    @pydantic.field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        return DDRDateStatus.validate(value)


class DDRDateStartedEvent(BaseSchemaModel):
    date: str


class DDRDateCompleteEvent(BaseSchemaModel):
    date: str
    status: str
    occurrences_count: int = 0

    @pydantic.field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in (DDRDateStatus.SUCCESS, DDRDateStatus.WARNING):
            raise ValueError("Invalid completed DDR date status")
        return value


class DDRDateFailedEvent(BaseSchemaModel):
    date: str
    error: str
    raw_response_id: str


class DDRProcessingCompleteEvent(BaseSchemaModel):
    total_dates: int
    failed_dates: int
    warning_dates: int
    total_occurrences: int = 0


class DDRDateInResponse(DDRDateBase):
    id: str
    created_at: int
    updated_at: int


class DDRDetailResponse(DDRListItemResponse):
    dates: list[DDRDateInResponse] = pydantic.Field(default_factory=list)


class ProcessingQueueInCreate(BaseSchemaModel):
    ddr_id: str
    position: int


class ProcessingQueueInResponse(ProcessingQueueInCreate):
    id: str
    created_at: int


class PipelineRunInCreate(BaseSchemaModel):
    ddr_date_id: str
    gemini_input_tokens: int | None = None
    gemini_output_tokens: int | None = None
    cost_usd: Decimal | None = None


class PipelineRunInResponse(PipelineRunInCreate):
    id: str
    created_at: int


class DDRExtractionSchemaModel(BaseSchemaModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        validate_assignment=True,
        extra="forbid",
    )


class DDRExtractionTimeLog(DDRExtractionSchemaModel):
    start_time: str
    end_time: str
    duration_hours: float
    activity: str
    depth_md: float | None = None
    comment: str | None = None
    page_number: int | None = None


class DDRExtractionMudRecord(DDRExtractionSchemaModel):
    depth_md: float
    mud_weight: float
    viscosity: float | None = None
    ph: float | None = None
    comment: str | None = None


class DDRExtractionDeviationSurvey(DDRExtractionSchemaModel):
    depth_md: float
    inclination: float
    azimuth: float
    tvd: float | None = None


class DDRExtractionBitRecord(DDRExtractionSchemaModel):
    bit_number: str
    bit_size: float
    depth_in: float
    depth_out: float
    hours: float | None = None
    comment: str | None = None


class DDRExtractionPayload(DDRExtractionSchemaModel):
    time_logs: list[DDRExtractionTimeLog]
    mud_records: list[DDRExtractionMudRecord]
    deviation_surveys: list[DDRExtractionDeviationSurvey]
    bit_records: list[DDRExtractionBitRecord]
    well_name: str | None = None
    surface_location: str | None = None
