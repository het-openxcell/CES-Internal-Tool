import json
from functools import lru_cache
from pathlib import Path
from typing import Any


class DDRExtractionSchema:
    def __init__(self, schema: dict[str, Any]):
        self._schema = schema

    @property
    def raw(self) -> dict[str, Any]:
        return self._schema

    def section_names(self) -> tuple[str, ...]:
        return tuple(self._schema.get("properties", {}).keys())

    def gemini_response_schema(self) -> dict[str, Any]:
        return json.loads(json.dumps(self._schema))


@lru_cache(maxsize=1)
def load_ddr_extraction_schema() -> DDRExtractionSchema:
    schema = json.loads((Path(__file__).parent / "ddr_schema.json").read_text(encoding="utf-8"))
    return DDRExtractionSchema(schema)
