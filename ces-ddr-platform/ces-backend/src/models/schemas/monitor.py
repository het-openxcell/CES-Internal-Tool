from pydantic import ConfigDict

from src.models.schemas.base import BaseSchemaModel


class MonitorMetrics(BaseSchemaModel):
    ddrs_this_week: int
    occurrences_extracted: int
    ai_cost_weekly: float
    failed_dates: int
    corrections_this_week: int
    avg_processing_seconds: float
    exports_this_week: int
    uptime_month: float


class QueueItemResponse(BaseSchemaModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    file_path: str
    well_name: str | None
    operator: str | None
    area: str | None
    status: str
    date_total: int
    date_success: int
    date_failed: int
    date_warning: int
    created_at: int
    updated_at: int


class OccurrenceEditResponse(BaseSchemaModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    occurrence_id: str
    ddr_id: str
    field: str
    original_value: str | None
    corrected_value: str | None
    reason: str | None
    created_by: str | None
    created_at: int


class OccurrencePatchRequest(BaseSchemaModel):
    field: str
    value: str | None
    reason: str | None = None
