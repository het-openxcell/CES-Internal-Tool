import asyncio
import json
from typing import Any

from google import genai
from google.genai import types
from pydantic import BaseModel

from src.config.manager import settings
from src.constants.occurrence import (
    DEFAULT_INTERMEDIATE_SHOE_DEPTH,
    DEFAULT_SURFACE_SHOE_DEPTH,
    OCCURRENCE_BACKOFF_SECONDS,
    OCCURRENCE_RATE_LIMIT_SIGNALS,
    VALID_OCCURRENCE_TYPES,
)
from src.constants.prompts import LLMPrompts
from src.models.schemas.ddr import DDRDateStatus
from src.services.langsmith_tracing import LangSmithTracingService
from src.services.occurrence.classify import OccurrenceClassifier
from src.services.occurrence.dedup import OccurrenceDeduplicator
from src.services.occurrence.density_join import DensityJoinService
from src.utilities.logging.logger import logger


class LLMOccurrenceItem(BaseModel):
    date: str
    type: str
    mmd: float | None = None
    notes: str | None = None
    page_number: int | None = None
    source_log_indexes: list[int] | None = None


class LLMOccurrenceResponse(BaseModel):
    occurrences: list[LLMOccurrenceItem]


class OccurrencePageNumberResolver:
    def __init__(self, rows: list[Any]) -> None:
        self._time_logs_by_date = self._build_time_logs_by_date(rows)
        self._valid_pages_by_date = self._build_valid_pages_by_date()

    def resolve(self, item: LLMOccurrenceItem) -> int | None:
        page_from_indexes = self._from_indexes(item.date, item.source_log_indexes)
        if page_from_indexes is not None:
            return page_from_indexes
        valid_pages = self._valid_pages_by_date.get(item.date, set())
        if isinstance(item.page_number, int) and item.page_number in valid_pages:
            return item.page_number
        return None

    def _from_indexes(self, date: str, indexes: list[int] | None) -> int | None:
        if not indexes:
            return None
        time_logs = self._time_logs_by_date.get(date, [])
        for index in indexes:
            if not isinstance(index, int) or index < 0 or index >= len(time_logs):
                continue
            time_log = time_logs[index]
            if not isinstance(time_log, dict):
                continue
            page_number = time_log.get("page_number")
            if isinstance(page_number, int):
                return page_number
        return None

    def _build_time_logs_by_date(self, rows: list[Any]) -> dict[str, list[Any]]:
        mapped: dict[str, list[Any]] = {}
        for row in rows:
            final_json = row.final_json or {}
            raw_time_logs = final_json.get("time_logs")
            mapped[row.date] = raw_time_logs if isinstance(raw_time_logs, list) else []
        return mapped

    def _build_valid_pages_by_date(self) -> dict[str, set[int]]:
        mapped: dict[str, set[int]] = {}
        for date, time_logs in self._time_logs_by_date.items():
            mapped[date] = {
                time_log["page_number"]
                for time_log in time_logs
                if isinstance(time_log, dict) and isinstance(time_log.get("page_number"), int)
            }
        return mapped


class LLMOccurrenceGenerationService:
    def __init__(self, ddr_date_repository: Any, occurrence_repository: Any) -> None:
        self.ddr_date_repository = ddr_date_repository
        self.occurrence_repository = occurrence_repository
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model = settings.GEMINI_MODEL

    def is_rate_limit(self, exc: Exception) -> bool:
        status_code = getattr(exc, "status_code", None)
        code = getattr(exc, "code", None)
        status = status_code if status_code is not None else code
        if status == 429:
            return True
        lowered = f"{type(exc).__name__} {exc}".lower()
        return any(signal in lowered for signal in OCCURRENCE_RATE_LIMIT_SIGNALS)

    def _format_time_logs(self, rows: list[Any]) -> str:
        blocks: list[str] = []
        for row in rows:
            final_json = row.final_json or {}
            raw_tl = final_json.get("time_logs")
            time_logs = raw_tl if isinstance(raw_tl, list) else []
            lines = [f"=== {row.date} ==="]
            for i, tl in enumerate(time_logs):
                if not isinstance(tl, dict):
                    continue
                start = tl.get("start_time") or "?"
                end = tl.get("end_time") or "?"
                duration = tl.get("duration_hours")
                depth = tl.get("depth_md")
                page_number = tl.get("page_number")
                activity = tl.get("activity") or ""
                comment = tl.get("comment") or ""
                text = f"{activity} {comment}".strip() if comment else activity
                depth_str = f"{depth}m" if depth is not None else "-"
                duration_str = f"{duration}h" if duration is not None else "?"
                page_str = f"pg.{page_number}" if page_number is not None else "pg.?"
                lines.append(f"[{i}] {start}-{end} ({duration_str}) | {depth_str} | {page_str} | {text}")
            blocks.append("\n".join(lines))
        return "\n\n".join(blocks)

    async def _previous_occurrences_text(self, ddr_id: str) -> str:
        previous = await self.occurrence_repository.get_by_ddr_id_filtered(ddr_id)
        lines = []
        for occurrence in previous:
            date = getattr(occurrence, "date", None) or "?"
            occurrence_type = getattr(occurrence, "type", None) or "?"
            mmd = getattr(occurrence, "mmd", None)
            notes = getattr(occurrence, "notes", None) or ""
            lines.append(f"{date} | {occurrence_type} | {mmd} | {notes}".strip())
        return "\n".join(lines)

    def _build_prompt(self, time_logs_text: str, previous_occurrences_text: str = "") -> str:
        valid_types_str = ", ".join(sorted(VALID_OCCURRENCE_TYPES))
        return LLMPrompts.occurrence_generation(
            time_logs_text=time_logs_text,
            valid_types=valid_types_str,
            previous_occurrences_text=previous_occurrences_text,
        )

    @LangSmithTracingService.trace(
        name="ddr-occurrence-generation",
        run_type="chain",
        process_inputs=LangSmithTracingService.safe_inputs,
        process_outputs=LangSmithTracingService.safe_outputs,
    )
    async def generate_for_ddr(
        self,
        ddr_id: str,
        ddr_well_name: str | None = None,
        ddr_surface_location: str | None = None,
        surface_shoe: float = DEFAULT_SURFACE_SHOE_DEPTH,
        intermediate_shoe: float = DEFAULT_INTERMEDIATE_SHOE_DEPTH,
    ) -> int:
        if surface_shoe >= intermediate_shoe:
            raise ValueError(
                f"surface_shoe ({surface_shoe}) must be less than intermediate_shoe ({intermediate_shoe})"
            )

        rows = await self.ddr_date_repository.read_dates_by_ddr_id(ddr_id)
        successful_rows = [r for r in rows if r.status == DDRDateStatus.SUCCESS]
        if not successful_rows:
            return 0

        time_logs_text = self._format_time_logs(successful_rows)
        previous_occurrences_text = await self._previous_occurrences_text(ddr_id)
        prompt = self._build_prompt(time_logs_text, previous_occurrences_text=previous_occurrences_text)
        result_text: str | None = None
        last_error: Exception | None = None
        for attempt, backoff in enumerate(OCCURRENCE_BACKOFF_SECONDS):
            try:
                response = await self.client.aio.models.generate_content(
                    model=self.model,
                    contents=[types.Part.from_text(text=prompt)],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=LLMOccurrenceResponse.model_json_schema(),
                    ),
                )
                result_text = response.text
                break
            except Exception as exc:
                if self.is_rate_limit(exc):
                    last_error = exc
                    logger.warning(
                        f"LLM occurrence rate limit (attempt {attempt + 1}/4): {exc} - retrying in {backoff:.1f}s"
                    )
                    await asyncio.sleep(backoff)
                else:
                    raise
        else:
            raise RuntimeError("LLM call failed after retries") from last_error

        logger.debug(f"LLM raw occurrence response: {result_text}")

        try:
            parsed = json.loads(result_text or "")
            llm_response = LLMOccurrenceResponse(**parsed)
        except Exception as exc:
            logger.error(f"LLM occurrence parse failed: {exc} | raw: {(result_text or '')[:500]}")
            return 0

        date_map: dict[str, tuple[Any, dict]] = {}
        for row in successful_rows:
            if row.date not in date_map:
                date_map[row.date] = (row.id, row.final_json or {})
            else:
                logger.warning(
                    f"ddr_id={ddr_id}: duplicate date {row.date} in successful rows - keeping first"
                )

        page_number_resolver = OccurrencePageNumberResolver(successful_rows)
        all_occurrences: list[dict] = []
        for item in llm_response.occurrences:
            if item.type not in VALID_OCCURRENCE_TYPES:
                logger.warning(
                    f"ddr_id={ddr_id}: LLM returned unknown occurrence type {item.type!r} - skipping"
                )
                continue
            if item.date not in date_map:
                logger.warning(
                    f"ddr_id={ddr_id}: LLM returned date {item.date!r} not in successful rows - skipping"
                )
                continue
            ddr_date_id, final_json = date_map[item.date]
            raw_mr = final_json.get("mud_records")
            mud_records = raw_mr if isinstance(raw_mr, list) else []
            section = OccurrenceClassifier.classify_section(item.mmd, surface_shoe, intermediate_shoe)
            density = DensityJoinService.density_join(item.mmd, mud_records)
            all_occurrences.append({
                "ddr_id": ddr_id,
                "ddr_date_id": ddr_date_id,
                "type": item.type,
                "mmd": item.mmd,
                "section": section,
                "density": density,
                "well_name": ddr_well_name,
                "surface_location": ddr_surface_location,
                "notes": item.notes,
                "date": item.date,
                "page_number": page_number_resolver.resolve(item),
            })

        deduped = OccurrenceDeduplicator.dedup(all_occurrences)
        await self.occurrence_repository.replace_for_ddr(ddr_id, deduped)
        return len(deduped)
