import asyncio
import json
import logging
from typing import Any

from google import genai
from google.genai import types
from pydantic import BaseModel

from src.config.manager import settings
from src.models.schemas.ddr import DDRDateStatus
from src.services.langsmith_tracing import LangSmithTracingService
from src.services.occurrence.classify import (
    DEFAULT_INTERMEDIATE_SHOE_DEPTH,
    DEFAULT_SURFACE_SHOE_DEPTH,
    VALID_OCCURRENCE_TYPES,
    classify_section,
)
from src.services.occurrence.dedup import dedup
from src.services.occurrence.density_join import density_join

logger = logging.getLogger(__name__)


class LLMOccurrenceItem(BaseModel):
    date: str
    type: str
    mmd: float | None = None
    notes: str | None = None


class LLMOccurrenceResponse(BaseModel):
    occurrences: list[LLMOccurrenceItem]


_RATE_LIMIT_SIGNALS = (
    "429",
    "rate limit",
    "ratelimit",
    "resource_exhausted",
    "quota",
    "too many requests",
)
_BACKOFF_SECONDS = (1.0, 2.0, 4.0, 8.0)


class LLMOccurrenceGenerationService:
    def __init__(self, ddr_date_repository: Any, occurrence_repository: Any) -> None:
        self.ddr_date_repository = ddr_date_repository
        self.occurrence_repository = occurrence_repository
        self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self._model = settings.GEMINI_MODEL

    def _is_rate_limit(self, exc: Exception) -> bool:
        status_code = getattr(exc, "status_code", None)
        code = getattr(exc, "code", None)
        status = status_code if status_code is not None else code
        if status == 429:
            return True
        lowered = f"{type(exc).__name__} {exc}".lower()
        return any(signal in lowered for signal in _RATE_LIMIT_SIGNALS)

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
                activity = tl.get("activity") or ""
                comment = tl.get("comment") or ""
                text = f"{activity} {comment}".strip() if comment else activity
                depth_str = f"{depth}m" if depth is not None else "-"
                duration_str = f"{duration}h" if duration is not None else "?"
                lines.append(f"[{i}] {start}-{end} ({duration_str}) | {depth_str} | {text}")
            blocks.append("\n".join(lines))
        return "\n\n".join(blocks)

    def _format_existing(self, occurrences: list[Any]) -> str:
        if not occurrences:
            return ""
        lines: list[str] = []
        for occ in occurrences:
            if isinstance(occ, dict):
                date = occ.get("date", "")
                occ_type = occ.get("type", "")
                mmd = occ.get("mmd")
                notes = occ.get("notes")
            else:
                date = getattr(occ, "date", "")
                occ_type = getattr(occ, "type", "")
                mmd = getattr(occ, "mmd", None)
                notes = getattr(occ, "notes", None)
            lines.append(f"- {date} | {occ_type} | {mmd} | {notes}")
        return "\n".join(lines)

    def _build_prompt(self, time_logs_text: str, existing_text: str) -> str:
        valid_types_str = ", ".join(sorted(VALID_OCCURRENCE_TYPES))
        prompt = (
            "You are a drilling engineering expert. From current time logs below, identify final occurrence set —\n"
            "drilling events or problems. Use ONLY the valid types listed.\n\n"
            f"VALID TYPES: {valid_types_str}\n\n"
            f"CURRENT TIME LOGS:\n{time_logs_text}"
        )
        if existing_text:
            prompt += (
                "\n\nPREVIOUSLY GENERATED OCCURRENCES:\n"
                f"{existing_text}\n\n"
                "Validate previous occurrences against current time logs. Keep valid occurrences, "
                "remove invalid or stale ones, update changed date/type/mmd/notes values, and add missing occurrences."
            )
        prompt += (
            "\n\nReturn one final JSON object with key 'occurrences'. "
            "Do not return actions or explanations. "
            "Each occurrence must have: date (YYYYMMDD string), type (from valid types), "
            "mmd (float or null), notes (string or null)."
        )
        return prompt

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

        existing = await self.occurrence_repository.get_by_ddr_id_filtered(
            ddr_id, None, None, None, None
        )

        time_logs_text = self._format_time_logs(successful_rows)
        existing_text = self._format_existing(existing)
        prompt = self._build_prompt(time_logs_text, existing_text)
        logger.debug("LLM occurrence prompt: {prompt}")
        result_text: str | None = None
        last_error: Exception | None = None
        for attempt, backoff in enumerate(_BACKOFF_SECONDS):
            try:
                response = await self._client.aio.models.generate_content(
                    model=self._model,
                    contents=[types.Part.from_text(text=prompt)],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=LLMOccurrenceResponse.model_json_schema(),
                    ),
                )
                result_text = response.text
                break
            except Exception as exc:
                if self._is_rate_limit(exc):
                    last_error = exc
                    logger.warning(
                        "LLM occurrence rate limit (attempt %d/4): %s — retrying in %.1fs",
                        attempt + 1,
                        exc,
                        backoff,
                    )
                    await asyncio.sleep(backoff)
                else:
                    raise
        else:
            raise RuntimeError("LLM call failed after retries") from last_error

        logger.debug("LLM raw occurrence response: %s", result_text)

        try:
            parsed = json.loads(result_text or "")
            llm_response = LLMOccurrenceResponse(**parsed)
        except Exception as exc:
            logger.error("LLM occurrence parse failed: %s | raw: %.500s", exc, result_text)
            return 0

        # Build date_map — if two rows share same date, keep first
        date_map: dict[str, tuple[Any, dict]] = {}
        for row in successful_rows:
            if row.date not in date_map:
                date_map[row.date] = (row.id, row.final_json or {})
            else:
                logger.warning(
                    "ddr_id=%s: duplicate date %s in successful rows — keeping first",
                    ddr_id,
                    row.date,
                )

        all_occurrences: list[dict] = []
        for item in llm_response.occurrences:
            if item.type not in VALID_OCCURRENCE_TYPES:
                logger.warning(
                    "ddr_id=%s: LLM returned unknown occurrence type %r — skipping",
                    ddr_id,
                    item.type,
                )
                continue
            if item.date not in date_map:
                logger.warning(
                    "ddr_id=%s: LLM returned date %r not in successful rows — skipping",
                    ddr_id,
                    item.date,
                )
                continue
            ddr_date_id, final_json = date_map[item.date]
            raw_mr = final_json.get("mud_records")
            mud_records = raw_mr if isinstance(raw_mr, list) else []
            section = classify_section(item.mmd, surface_shoe, intermediate_shoe)
            density = density_join(item.mmd, mud_records)
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
            })

        deduped = dedup(all_occurrences)
        await self.occurrence_repository.replace_for_ddr(ddr_id, deduped)
        return len(deduped)
