import asyncio
from dataclasses import dataclass
from typing import Any, Protocol

from src.config.manager import settings
from src.constants.pipeline import DDR_METADATA_KEYS, GEMINI_BACKOFF_SECONDS, GEMINI_RATE_LIMIT_SIGNALS
from src.constants.prompts import LLMPrompts
from src.resources.ddr_schema import DDRExtractionSchema, load_ddr_extraction_schema
from src.services.langsmith_tracing import LangSmithTracingService


class ExtractionError(Exception):
    def __init__(self, detail: str = "extraction_failed"):
        self.detail = detail
        super().__init__(detail)


class RateLimitError(ExtractionError):
    def __init__(self, detail: str = "rate_limited"):
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

        self.client = genai.Client(api_key=api_key)

    @LangSmithTracingService.trace(
        name="gemini-ddr-extraction",
        run_type="llm",
        process_inputs=LangSmithTracingService.safe_inputs,
        process_outputs=LangSmithTracingService.safe_outputs,
    )
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
        response = await self.client.aio.models.generate_content(
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
    def __init__(
        self,
        client: GeminiClientProtocol | None = None,
        model: str | None = None,
        schema: DDRExtractionSchema | None = None,
        max_retries: int | None = None,
        sleep: Any = asyncio.sleep,
    ):
        self.client = client
        self.model = model or settings.GEMINI_MODEL
        self.schema_definition = schema or load_ddr_extraction_schema()
        configured_retries = settings.GEMINI_EXTRACTION_MAX_RETRIES if max_retries is None else max_retries
        self.max_retries = max(0, configured_retries)
        self.sleep = sleep

    @property
    def schema(self) -> DDRExtractionSchema:
        return self.schema_definition

    def resolve_client(self) -> GeminiClientProtocol:
        if self.client is None:
            api_key = settings.GEMINI_API_KEY
            if not api_key:
                raise ExtractionError("gemini_api_key_missing")
            self.client = GoogleGenAIClient(api_key=api_key)
        return self.client

    def build_prompt(self, date: str, original_page_numbers: list[int] | None = None) -> str:
        data_sections = [k for k in self.schema_definition.section_names() if k not in DDR_METADATA_KEYS]
        sections = ", ".join(data_sections)
        time_log_fields = ", ".join(
            self.schema_definition.raw["properties"]["time_logs"]["items"]["properties"].keys()
        )
        return LLMPrompts.ddr_extraction(
            date=date,
            sections=sections,
            time_log_fields=time_log_fields,
            original_page_numbers=original_page_numbers,
        )

    async def extract(
        self,
        *,
        date: str,
        pdf_bytes: bytes,
        original_page_numbers: list[int] | None = None,
    ) -> ExtractionResult:
        client = self.resolve_client()
        prompt = self.build_prompt(date, original_page_numbers=original_page_numbers)
        response_schema = self.schema_definition.gemini_response_schema()

        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                return await client.generate_content(
                    model=self.model,
                    pdf_bytes=pdf_bytes,
                    prompt=prompt,
                    response_schema=response_schema,
                )
            except Exception as exc:
                last_error = exc
                if not self.is_rate_limit(exc):
                    raise ExtractionError(f"gemini_call_failed: {exc}") from exc
                if attempt >= self.max_retries:
                    break
                await self.sleep(GEMINI_BACKOFF_SECONDS[min(attempt, len(GEMINI_BACKOFF_SECONDS) - 1)])

        if self.max_retries == 3:
            await self.sleep(GEMINI_BACKOFF_SECONDS[3])
        raise RateLimitError("rate_limited") from None if last_error is None else RateLimitError("rate_limited")

    def is_rate_limit(self, exc: Exception) -> bool:
        status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
        if status == 429:
            return True
        text = f"{type(exc).__name__} {exc}".lower()
        return any(signal in text for signal in GEMINI_RATE_LIMIT_SIGNALS)
