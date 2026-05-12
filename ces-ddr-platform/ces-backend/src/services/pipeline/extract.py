import asyncio
from dataclasses import dataclass
from typing import Any, Protocol

from src.config.manager import settings
from src.resources.ddr_schema import DDRExtractionSchema, load_ddr_extraction_schema


class ExtractionError(Exception):
    def __init__(self, detail: str = "extraction_failed"):
        self.detail = detail
        super().__init__(detail)


class RateLimitError(ExtractionError):
    def __init__(self, detail: str = "rate_limited"):
        super().__init__(detail)


class ExtractionValidationError(ExtractionError):
    def __init__(self, detail: str = "extraction_validation_failed"):
        super().__init__(detail)


@dataclass
class ExtractionResult:
    text: str
    input_tokens: int | None = None
    output_tokens: int | None = None


class GeminiClientProtocol(Protocol):
    async def generate_content(
        self,
        *,
        model: str,
        pdf_bytes: bytes,
        prompt: str,
        response_schema: dict[str, Any],
    ) -> ExtractionResult: ...


class GoogleGenAIClient:
    def __init__(self, api_key: str):
        from google import genai

        self._client = genai.Client(api_key=api_key)

    async def generate_content(
        self,
        *,
        model: str,
        pdf_bytes: bytes,
        prompt: str,
        response_schema: dict[str, Any],
    ) -> ExtractionResult:
        from google.genai import types

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_json_schema=response_schema,
        )
        contents = [
            types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
            prompt,
        ]
        response = await self._client.aio.models.generate_content(
            model=model,
            contents=contents,
            config=config,
        )
        usage = getattr(response, "usage_metadata", None)
        return ExtractionResult(
            text=getattr(response, "text", "") or "",
            input_tokens=getattr(usage, "prompt_token_count", None) if usage else None,
            output_tokens=getattr(usage, "candidates_token_count", None) if usage else None,
        )


class GeminiDDRExtractor:
    backoff_seconds: tuple[float, ...] = (1.0, 2.0, 4.0, 8.0)
    rate_limit_signals: tuple[str, ...] = ("429", "rate limit", "resource_exhausted", "quota", "too many requests")

    def __init__(
        self,
        client: GeminiClientProtocol | None = None,
        model: str | None = None,
        schema: DDRExtractionSchema | None = None,
        max_retries: int | None = None,
        sleep: Any = asyncio.sleep,
    ):
        self._client = client
        self._model = model or settings.GEMINI_MODEL
        self._schema = schema or load_ddr_extraction_schema()
        configured_retries = settings.GEMINI_EXTRACTION_MAX_RETRIES if max_retries is None else max_retries
        self._max_retries = max(0, configured_retries)
        self._sleep = sleep

    @property
    def schema(self) -> DDRExtractionSchema:
        return self._schema

    def _resolve_client(self) -> GeminiClientProtocol:
        if self._client is None:
            api_key = settings.GEMINI_API_KEY
            if not api_key:
                raise ExtractionError("gemini_api_key_missing")
            self._client = GoogleGenAIClient(api_key=api_key)
        return self._client

    def build_prompt(self, date: str) -> str:
        sections = ", ".join(self._schema.section_names())
        time_log_fields = ", ".join(
            self._schema.raw["properties"]["time_logs"]["items"]["properties"].keys()
        )
        return (
            "You are extracting structured data from a Daily Drilling Report (DDR) PDF for date "
            f"{date}. Return JSON with sections: {sections}. "
            "For 'time_logs', preserve the original row order from the report and emit fields in this "
            f"exact order per row: {time_log_fields}. Use null for missing optional values."
        )

    async def extract(self, *, date: str, pdf_bytes: bytes) -> ExtractionResult:
        client = self._resolve_client()
        prompt = self.build_prompt(date)
        response_schema = self._schema.gemini_response_schema()

        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                return await client.generate_content(
                    model=self._model,
                    pdf_bytes=pdf_bytes,
                    prompt=prompt,
                    response_schema=response_schema,
                )
            except Exception as exc:
                last_error = exc
                if not self._is_rate_limit(exc):
                    raise ExtractionError(f"gemini_call_failed: {exc}") from exc
                if attempt >= self._max_retries:
                    break
                await self._sleep(self.backoff_seconds[min(attempt, len(self.backoff_seconds) - 1)])

        if self._max_retries == 3:
            await self._sleep(self.backoff_seconds[3])
        raise RateLimitError("rate_limited") from None if last_error is None else RateLimitError("rate_limited")

    def _is_rate_limit(self, exc: Exception) -> bool:
        status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
        if status == 429:
            return True
        text = f"{type(exc).__name__} {exc}".lower()
        return any(signal in text for signal in self.rate_limit_signals)
