import json
from typing import Any

from google import genai
from google.genai import types

from src.config.manager import settings
from src.services.pipeline.embedding import TimeLogEmbeddingService
from src.utilities.logging.logger import logger


class NaturalLanguageQueryService:
    def __init__(
        self,
        embedding_service: TimeLogEmbeddingService | None = None,
        gemini_client: Any | None = None,
    ) -> None:
        self.embedding_service = embedding_service or TimeLogEmbeddingService()
        self.gemini_client = gemini_client or genai.Client(api_key=settings.GEMINI_API_KEY)

    async def answer(self, query: str) -> tuple[str, list[dict[str, Any]], list[str]]:
        expanded = await self.expand_query(query)
        logger.info(f"query_expanded original={query!r} expanded={expanded!r}")
        try:
            hits = await self.embedding_service.search_hybrid(
                queries=expanded,
                original_query=query,
                candidates_per_query=30,
                final_limit=20,
            )
        except Exception as exc:
            logger.warning(f"hybrid_search_failed error={exc}")
            hits = []
        context = self.hits_to_context(hits)
        answer = await self.generate_answer(query, context)
        return answer, hits, expanded

    async def expand_query(self, query: str) -> list[str]:
        prompt = (
            "You are a query expansion assistant for an oil and gas drilling database. "
            "Given a user's question, generate exactly 5 different search queries that together "
            "cover the full intent. Vary the phrasing, terminology, and angle - some technical, "
            "some descriptive. Each query should target different aspects or phrasings a driller "
            "might use in a time log. Return a JSON array of exactly 5 strings, nothing else.\n\n"
            f"User question: {query}"
        )
        response = await self.gemini_client.aio.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.7,
            ),
        )
        raw = response.text or "[]"
        try:
            queries = json.loads(raw)
            if isinstance(queries, list):
                return [str(query_item) for query_item in queries if query_item][:5]
        except json.JSONDecodeError:
            logger.warning(f"query_expansion_parse_failed raw={raw!r}")
        return [query]

    async def generate_answer(self, query: str, context: str) -> str:
        if not context:
            return "No relevant time log entries found in the database for your query."
        prompt = (
            "You are a drilling data analyst for Canadian Energy Services. "
            "Answer the following question using ONLY the time log entries provided below. "
            "Be concise and specific. Do NOT reference entry numbers, do NOT mention that context "
            "or data was provided to you, and do NOT reveal how you obtained the information. "
            "Respond as if you naturally know the answer from CES's DDR archive.\n\n"
            f"Time log entries:\n{context}\n\n"
            f"Question: {query}"
        )
        response = await self.gemini_client.aio.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.2),
        )
        return response.text or "Could not generate an answer."

    def hits_to_context(self, hits: list[dict[str, Any]]) -> str:
        blocks = []
        for index, hit in enumerate(hits, 1):
            payload = hit.get("payload") or {}
            text = payload.get("text") or "(no text)"
            blocks.append(f"[{index}]\n{text}")
        return "\n\n".join(blocks)
