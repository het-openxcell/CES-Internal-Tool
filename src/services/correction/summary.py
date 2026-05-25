import asyncio
import json
import re
import time
from typing import Any, Protocol

from pydantic import BaseModel, Field

from src.config.manager import settings
from src.repository.crud.correction_summary import CorrectionSummaryCRUDRepository
from src.services.langsmith_tracing import LangSmithTracingService
from src.utilities.logging.logger import logger


class EditSummaryResponse(BaseModel):
    summary_lines: list[str] = Field(min_length=1, max_length=3)


class CorrectionSummaryClientProtocol(Protocol):
    async def generate_summary(self, prompt: str) -> EditSummaryResponse: ...


class GoogleCorrectionSummaryClient:
    def __init__(self, api_key: str, model: str) -> None:
        from google import genai

        self.client = genai.Client(api_key=api_key)
        self.model = model

    @LangSmithTracingService.trace(
        name="correction-learning-summary",
        run_type="llm",
        process_inputs=LangSmithTracingService.safe_inputs,
        process_outputs=LangSmithTracingService.safe_outputs,
    )
    async def generate_summary(self, prompt: str) -> EditSummaryResponse:
        from google.genai import types

        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=[types.Part.from_text(text=prompt)],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=EditSummaryResponse.model_json_schema(),
            ),
        )
        return EditSummaryResponse.model_validate(json.loads(response.text or "{}"))


class CorrectionSummaryService:
    MAX_LOGS = 80
    MAX_LOG_TEXT = 260
    MAX_SUMMARY_LINE = 240
    MAX_EDIT_VALUE = 500
    LLM_TIMEOUT_SECONDS = 20

    def __init__(
        self,
        summary_repository: CorrectionSummaryCRUDRepository,
        client: CorrectionSummaryClientProtocol | None = None,
    ) -> None:
        self.summary_repository = summary_repository
        self.client = client

    def resolve_client(self) -> CorrectionSummaryClientProtocol | None:
        if self.client is not None:
            return self.client
        api_key = settings.GEMINI_API_KEY.strip() if settings.GEMINI_API_KEY else ""
        if not api_key:
            return None
        self.client = GoogleCorrectionSummaryClient(api_key, settings.GEMINI_MODEL)
        return self.client

    async def refresh_date_summary(self, ddr_date: Any, corrections: list[Any]) -> Any | None:
        if not corrections:
            return None
        source_logs = self.source_logs(ddr_date)
        edit_details = self.edit_details(corrections)
        summary = await self.generate_guarded_summary(ddr_date.date, source_logs, edit_details)
        return await self.summary_repository.upsert_date_summary(
            ddr_id=ddr_date.ddr_id,
            ddr_date_id=ddr_date.id,
            summary=summary,
            source_logs=source_logs,
            edit_details=edit_details,
            correction_count=len(corrections),
            updated_at=int(time.time()),
            commit=True,
        )

    async def generate_guarded_summary(self, date: str, source_logs: list[dict], edit_details: list[dict]) -> str:
        fallback = self.deterministic_summary(edit_details, source_logs)
        client = self.resolve_client()
        if client is None:
            return fallback
        try:
            response = await asyncio.wait_for(
                client.generate_summary(self.prompt(date, source_logs, edit_details)),
                timeout=self.LLM_TIMEOUT_SECONDS,
            )
            lines = self.clean_lines(response.summary_lines)
            if not self.is_grounded(lines, edit_details):
                return fallback
            return "\n".join(lines)
        except Exception as exc:
            logger.warning(f"correction_summary_generation_failed date={date} error={exc}")
            return fallback

    def source_logs(self, ddr_date: Any) -> list[dict]:
        final_json = ddr_date.final_json if isinstance(ddr_date.final_json, dict) else {}
        raw_logs = final_json.get("time_logs")
        logs = raw_logs if isinstance(raw_logs, list) else []
        result: list[dict] = []
        for log in logs[: self.MAX_LOGS]:
            if not isinstance(log, dict):
                continue
            text = " ".join(str(log.get(key) or "") for key in ("activity", "comment")).strip()
            result.append(
                {
                    "start": log.get("start_time"),
                    "end": log.get("end_time"),
                    "depth_md": log.get("depth_md"),
                    "page": log.get("page_number"),
                    "text": text[: self.MAX_LOG_TEXT],
                }
            )
        return result

    def bounded_text(self, value: Any) -> str:
        return str(value or "")[: self.MAX_EDIT_VALUE]

    def edit_details(self, corrections: list[Any]) -> list[dict]:
        return [
            {
                "field": correction.field_name,
                "before": self.bounded_text(correction.original_value),
                "after": self.bounded_text(correction.corrected_value),
                "reason": self.bounded_text(correction.reason),
                "created_at": correction.created_at,
            }
            for correction in corrections
        ]

    def prompt(self, date: str, source_logs: list[dict], edit_details: list[dict]) -> str:
        return (
            "Generate a correction learning summary for future DDR occurrence extraction.\n"
            "Rules:\n"
            "- Output JSON only: {\"summary_lines\":[...]} with 1 to 3 strings.\n"
            "- Each line must be actionable guidance, not a history note.\n"
            "- Preserve exact before -> after correction when practical.\n"
            "- Use only source logs, before/after values, and user reasons. Do not invent facts.\n"
            "- Prefer cue words from source logs that explain the edit.\n"
            "- If evidence is weak, say to apply only when source text explicitly supports it.\n\n"
            f"Date: {date}\n"
            f"Source logs: {json.dumps(source_logs, ensure_ascii=False)}\n"
            f"Edits: {json.dumps(edit_details, ensure_ascii=False)}"
        )

    def clean_lines(self, lines: list[str]) -> list[str]:
        cleaned: list[str] = []
        for line in lines[:3]:
            value = re.sub(r"^[-*\d.\s]+", "", line.strip())
            if value:
                cleaned.append(value[: self.MAX_SUMMARY_LINE])
        return cleaned

    def is_grounded(self, lines: list[str], edit_details: list[dict]) -> bool:
        if not lines:
            return False
        text = "\n".join(lines).lower()
        fields = {str(edit["field"]).lower() for edit in edit_details}
        after_values = {
            str(edit["after"]).lower().strip()
            for edit in edit_details
            if len(str(edit["after"]).strip()) >= 3
        }
        before_values = {
            str(edit["before"]).lower().strip()
            for edit in edit_details
            if len(str(edit["before"]).strip()) >= 3
        }
        value_matches = after_values or before_values
        return any(field in text for field in fields) and bool(value_matches) and (
            any(value[:40] in text for value in after_values) or any(value[:40] in text for value in before_values)
        )

    def deterministic_summary(self, edit_details: list[dict], source_logs: list[dict]) -> str:
        groups: dict[tuple[str, str, str], dict[str, Any]] = {}
        for edit in edit_details:
            key = (str(edit["field"]), str(edit["before"]), str(edit["after"]))
            if key not in groups:
                groups[key] = {"count": 0, "reasons": []}
            groups[key]["count"] += 1
            reason = str(edit.get("reason") or "").strip()
            if reason and reason not in groups[key]["reasons"]:
                groups[key]["reasons"].append(reason)

        lines: list[str] = []
        for (field, before, after), data in list(groups.items())[:2]:
            count = f" x{data['count']}" if data["count"] > 1 else ""
            reason = f" Reason: {data['reasons'][0]}" if data["reasons"] else ""
            lines.append(f"{field}: {before or '—'} -> {after or '—'}{count}.{reason}")

        cues = self.cues(source_logs)
        if cues:
            lines.append(f"Apply when source logs support cues: {', '.join(cues[:8])}.")
        return "\n".join(lines[:3])

    def cues(self, source_logs: list[dict]) -> list[str]:
        text = " ".join(str(log.get("text") or "") for log in source_logs).lower()
        candidates = [
            "pit gain",
            "flow check",
            "well flowing",
            "lost circulation",
            "kick",
            "gas",
            "flare",
            "stuck pipe",
            "ream",
            "back ream",
            "washout",
            "tight hole",
        ]
        return [cue for cue in candidates if cue in text]
