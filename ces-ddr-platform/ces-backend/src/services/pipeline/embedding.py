import asyncio
import math
import re
import uuid
from collections import Counter
from typing import Any, Protocol

from src.config.manager import settings
from src.constants.search import BM25_B, BM25_K1, RRF_K
from src.utilities.logging.logger import logger


class HybridSearchRanker:
    @classmethod
    def bm25_scores(cls, query: str, docs: list[str]) -> list[float]:
        query_tokens = cls.tokenize(query)
        doc_tokens = [cls.tokenize(doc) for doc in docs]
        doc_count = len(docs)
        if doc_count == 0 or not query_tokens:
            return [0.0] * doc_count
        avg_doc_length = sum(len(doc) for doc in doc_tokens) / doc_count
        document_frequency: dict[str, int] = {
            token: sum(1 for doc in doc_tokens if token in doc) for token in set(query_tokens)
        }
        inverse_frequency = {
            token: math.log(1 + (doc_count - frequency + 0.5) / (frequency + 0.5))
            for token, frequency in document_frequency.items()
        }
        scores = []
        for tokens in doc_tokens:
            doc_length = len(tokens)
            term_frequency = Counter(tokens)
            score = 0.0
            for query_token in query_tokens:
                if query_token not in term_frequency:
                    continue
                frequency = term_frequency[query_token]
                denominator = frequency + BM25_K1 * (
                    1 - BM25_B + BM25_B * (doc_length / avg_doc_length if avg_doc_length else 1.0)
                )
                score += inverse_frequency.get(query_token, 0.0) * (frequency * (BM25_K1 + 1) / denominator)
            scores.append(score)
        return scores

    @staticmethod
    def reciprocal_rank_fuse(rank_lists: list[list[int]], weights: list[float] | None = None) -> dict[int, float]:
        fused: dict[int, float] = {}
        resolved_weights = weights or [1.0] * len(rank_lists)
        for weight, ranks in zip(resolved_weights, rank_lists, strict=False):
            for rank, index in enumerate(ranks):
                fused[index] = fused.get(index, 0.0) + weight / (RRF_K + rank + 1)
        return fused

    @staticmethod
    def tokenize(text: str) -> list[str]:
        return re.findall(r"[a-z0-9]+", (text or "").lower())


class EmbeddingClientProtocol(Protocol):
    async def embed_content(self, *, model: str, contents: list[str]) -> list[list[float]]: ...


class QdrantClientProtocol(Protocol):
    async def ensure_collection(self, *, collection_name: str, vector_size: int) -> None: ...

    async def upsert(self, *, collection_name: str, points: list[dict[str, Any]]) -> None: ...

    async def search(self, *, collection_name: str, vector: list[float], limit: int) -> list[dict[str, Any]]:
        ...


class GoogleEmbeddingClient:
    def __init__(self, api_key: str) -> None:
        from google import genai

        self.client = genai.Client(api_key=api_key)

    async def embed_content(self, *, model: str, contents: list[str]) -> list[list[float]]:
        response = await self.client.aio.models.embed_content(model=model, contents=contents)
        embeddings = getattr(response, "embeddings", None) or []
        return [list(embedding.values) for embedding in embeddings]


class QdrantTimeLogClient:
    def __init__(self, url: str, api_key: str | None = None) -> None:
        from qdrant_client import AsyncQdrantClient

        secure = url.startswith("https://")
        if api_key and not secure:
            logger.warning("qdrant_api_key_suppressed: QDRANT_URL is not HTTPS; api_key will not be sent")
        self.client = AsyncQdrantClient(url=url, api_key=api_key if secure else None)

    async def ensure_collection(self, *, collection_name: str, vector_size: int) -> None:
        from qdrant_client.http.exceptions import UnexpectedResponse
        from qdrant_client.models import Distance, VectorParams

        exists = await self.client.collection_exists(collection_name=collection_name)
        if not exists:
            try:
                await self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
                )
            except UnexpectedResponse as exc:
                if exc.status_code != 409:
                    raise

    async def upsert(self, *, collection_name: str, points: list[dict[str, Any]]) -> None:
        from qdrant_client.models import PointStruct

        qdrant_points = [
            PointStruct(id=point["id"], vector=point["vector"], payload=point["payload"]) for point in points
        ]
        await self.client.upsert(collection_name=collection_name, points=qdrant_points, wait=True)

    async def search(self, *, collection_name: str, vector: list[float], limit: int) -> list[dict[str, Any]]:
        response = await self.client.query_points(
            collection_name=collection_name,
            query=vector,
            limit=limit,
            with_payload=True,
        )
        return [{"payload": hit.payload, "score": hit.score} for hit in response.points]


class TimeLogEmbeddingService:
    def __init__(
        self,
        embedding_client: EmbeddingClientProtocol | None = None,
        qdrant_client: QdrantClientProtocol | None = None,
        collection_name: str | None = None,
        embedding_model: str | None = None,
        vector_size: int | None = None,
        service_logger: Any | None = None,
    ) -> None:
        self.embedding_client = embedding_client
        self.qdrant_client = qdrant_client
        self.collection_name = collection_name or settings.QDRANT_COLLECTION_DDR_TIME_LOGS
        self.embedding_model = embedding_model or settings.GEMINI_EMBEDDING_MODEL
        self.vector_size = vector_size or settings.GEMINI_EMBEDDING_DIMENSION
        self.logger = service_logger or logger

    async def embed_successful_date(self, ddr_date: Any) -> None:
        try:
            rows = self.time_log_points(ddr_date)
            if not rows:
                return
            contents = [row["text"] for row in rows]
            vectors = await self.resolve_embedding_client().embed_content(
                model=self.embedding_model,
                contents=contents,
            )
            points = [
                {
                    "id": row["id"],
                    "vector": vector,
                    "payload": row["payload"],
                }
                for row, vector in zip(rows, vectors, strict=False)
            ]
            if not points:
                return
            qdrant = self.resolve_qdrant_client()
            await qdrant.ensure_collection(collection_name=self.collection_name, vector_size=self.vector_size)
            await qdrant.upsert(collection_name=self.collection_name, points=points)
        except Exception as exc:
            self.logger.warning(
                "time_log_embedding_failed "
                f"ddr_id={getattr(ddr_date, 'ddr_id', None)} "
                f"ddr_date_id={getattr(ddr_date, 'id', None)} "
                f"date={getattr(ddr_date, 'date', None)} "
                f"error={exc}"
            )

    async def search_hybrid(
        self,
        queries: list[str],
        original_query: str,
        candidates_per_query: int = 30,
        final_limit: int = 20,
    ) -> list[dict[str, Any]]:
        if not queries:
            queries = [original_query]
        vectors = await self.resolve_embedding_client().embed_content(
            model=self.embedding_model,
            contents=queries,
        )
        qdrant = self.resolve_qdrant_client()
        per_query_results = await asyncio.gather(
            *[
                qdrant.search(
                    collection_name=self.collection_name,
                    vector=vector,
                    limit=candidates_per_query,
                )
                for vector in vectors
                if vector
            ],
            return_exceptions=True,
        )
        candidates: dict[str, dict[str, Any]] = {}
        per_query_ranks: list[list[str]] = []
        for result in per_query_results:
            if isinstance(result, Exception):
                continue
            ranks: list[str] = []
            for hit in result:
                payload = hit.get("payload") or {}
                key = payload.get("text") or f"{payload.get('date','')}:{payload.get('ddr_date_id','')}"
                if not key:
                    continue
                ranks.append(key)
                if key not in candidates or hit.get("score", 0) > candidates[key].get("score", 0):
                    candidates[key] = hit
            per_query_ranks.append(ranks)

        if not candidates:
            return []

        keys = list(candidates.keys())
        index_by_key = {k: i for i, k in enumerate(keys)}
        docs = [(candidates[k].get("payload") or {}).get("text") or "" for k in keys]

        dense_rank_lists = [
            [index_by_key[k] for k in ranks if k in index_by_key]
            for ranks in per_query_ranks
        ]

        bm25 = HybridSearchRanker.bm25_scores(original_query, docs)
        sparse_rank = sorted(range(len(keys)), key=lambda i: bm25[i], reverse=True)

        n_dense = len(dense_rank_lists)
        dense_weight = 0.5 / n_dense if n_dense else 0.0
        weights = [dense_weight] * n_dense + [0.5]
        fused = HybridSearchRanker.reciprocal_rank_fuse([*dense_rank_lists, sparse_rank], weights=weights)
        ordered = sorted(fused.items(), key=lambda kv: kv[1], reverse=True)[:final_limit]

        return [candidates[keys[idx]] for idx, _ in ordered]

    def time_log_points(self, ddr_date: Any) -> list[dict[str, Any]]:
        final_json = getattr(ddr_date, "final_json", None)
        if not isinstance(final_json, dict):
            return []
        time_logs = final_json.get("time_logs")
        if not isinstance(time_logs, list):
            return []

        well_name = final_json.get("well_name") or "Unknown"
        surface_location = final_json.get("surface_location") or "Unknown"
        date = getattr(ddr_date, "date", None) or "Unknown"

        log_lines = []
        for row in time_logs:
            if not isinstance(row, dict):
                continue
            log_text = self.row_log_text(row)
            if not log_text:
                continue
            time_from = row.get("time_from") or row.get("start_time") or ""
            time_to = row.get("time_to") or row.get("end_time") or ""
            time_stamp = f"{time_from} : {time_to}".strip(" :") or "Unknown"
            log_lines.append(f"    Time Stamp: {time_stamp} Logs: {log_text}")

        if not log_lines:
            return []

        text = (
            f"Date: {date}\n"
            f"Well Name: {well_name}\n"
            f"Surface Location: {surface_location}\n"
            + "\n".join(log_lines)
        )

        return [
            {
                "id": str(uuid.uuid5(uuid.NAMESPACE_URL, str(ddr_date.id))),
                "text": text,
                "payload": self.payload(ddr_date, final_json, text=text),
            }
        ]

    def row_log_text(self, row: dict[str, Any]) -> str:
        parts = [
            str(row.get("activity") or "").strip(),
            str(row.get("details") or "").strip(),
            str(row.get("comment") or "").strip(),
        ]
        return " | ".join(part for part in parts if part)

    def payload(self, ddr_date: Any, final_json: dict[str, Any], text: str = "") -> dict[str, Any]:
        return {
            "ddr_id": getattr(ddr_date, "ddr_id", None),
            "ddr_date_id": getattr(ddr_date, "id", None),
            "date": getattr(ddr_date, "date", None),
            "well_name": final_json.get("well_name"),
            "surface_location": final_json.get("surface_location"),
            "text": text,
        }

    def resolve_embedding_client(self) -> EmbeddingClientProtocol:
        if self.embedding_client is None:
            if not settings.GEMINI_API_KEY:
                raise ValueError("gemini_api_key_missing")
            self.embedding_client = GoogleEmbeddingClient(settings.GEMINI_API_KEY)
        return self.embedding_client

    def resolve_qdrant_client(self) -> QdrantClientProtocol:
        if self.qdrant_client is None:
            api_key = settings.QDRANT_API_KEY.get_secret_value() if settings.QDRANT_API_KEY else None
            self.qdrant_client = QdrantTimeLogClient(url=settings.QDRANT_URL, api_key=api_key)
        return self.qdrant_client
