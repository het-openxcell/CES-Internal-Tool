import json
from pathlib import Path

import pydantic
import pytest

from src.models.schemas.ddr import DDRExtractionPayload
from src.resources.ddr_schema import DDRExtractionSchema, load_ddr_extraction_schema

FIXTURE = Path(__file__).parent / "fixtures" / "expected_timelogs.json"


def test_schema_loads_required_sections() -> None:
    schema = load_ddr_extraction_schema()
    sections = schema.section_names()
    assert "time_logs" in sections
    assert "mud_records" in sections
    assert "deviation_surveys" in sections
    assert "bit_records" in sections


def test_schema_returns_gemini_compatible_dict_copy() -> None:
    schema = load_ddr_extraction_schema()
    first = schema.gemini_response_schema()
    second = schema.gemini_response_schema()
    first["properties"]["time_logs"]["mutated"] = True
    assert "mutated" not in second["properties"]["time_logs"]
    assert first["type"] == "object"


def test_payload_validates_fixture_and_preserves_time_log_order() -> None:
    expected = json.loads(FIXTURE.read_text())
    payload = DDRExtractionPayload.model_validate(expected)

    fixture_activities = [row["activity"] for row in expected["time_logs"]]
    payload_activities = [row.activity for row in payload.time_logs]
    assert payload_activities == fixture_activities


def test_payload_rejects_missing_required_field() -> None:
    bad = {
        "time_logs": [{"start_time": "00:00", "end_time": "06:00", "duration_hours": 6.0}],
        "mud_records": [],
        "deviation_surveys": [],
        "bit_records": [],
    }
    with pytest.raises(pydantic.ValidationError):
        DDRExtractionPayload.model_validate(bad)


def test_payload_rejects_unexpected_fields() -> None:
    payload = json.loads(FIXTURE.read_text())
    payload["time_logs"][0]["hallucinated_field"] = "unexpected"
    with pytest.raises(pydantic.ValidationError):
        DDRExtractionPayload.model_validate(payload)


def test_schema_class_exposes_raw_dict() -> None:
    schema = DDRExtractionSchema({"type": "object", "properties": {"x": {"type": "string"}}})
    assert schema.raw["type"] == "object"
    assert schema.section_names() == ("x",)
