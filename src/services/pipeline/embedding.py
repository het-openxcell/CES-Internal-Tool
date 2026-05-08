import logging
import uuid
from typing import Any, Protocol

from src.config.manager import settings

_log = logging.getLogger(__name__)


class EmbeddingClientProtocol(Protocol):
    async def embed_content(self, *, model: str, contents: list[str]) -> list[list[float]]: ...


class QdrantClientProtocol(Protocol):
    async def ensure_collection(self, *, collection_name: str, vector_size: int) -> None: ...

    async def upsert(self, *, collection_name: str, points: list[dict[str, Any]]) -> None: ...


class GoogleEmbeddingClient:
    def __init__(self, api_key: str) -> None:
        from google import genai

        self._client = genai.Client(api_key=api_key)

    async def embed_content(self, *, model: str, contents: list[str]) -> list[list[float]]:
        response = await self._client.aio.models.embed_content(model=model, contents=contents)
        embeddings = getattr(response, "embeddings", None) or []
        return [list(embedding.values) for embedding in embeddings]


class QdrantTimeLogClient:
    def __init__(self, url: str, api_key: str | None = None) -> None:
        from qdrant_client import AsyncQdrantClient

        secure = url.startswith("https://")
        if api_key and not secure:
            _log.warning("qdrant_api_key_suppressed: QDRANT_URL is not HTTPS; api_key will not be sent")
        self._client = AsyncQdrantClient(url=url, api_key=api_key if secure else None)

    async def ensure_collection(self, *, collection_name: str, vector_size: int) -> None:
        from qdrant_client.http.exceptions import UnexpectedResponse
        from qdrant_client.models import Distance, VectorParams

        exists = await self._client.collection_exists(collection_name=collection_name)
        if not exists:
            try:
                await self._client.create_collection(
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
        await self._client.upsert(collection_name=collection_name, points=qdrant_points, wait=True)


class TimeLogEmbeddingService:
    def __init__(
        self,
        embedding_client: EmbeddingClientProtocol | None = None,
        qdrant_client: QdrantClientProtocol | None = None,
        collection_name: str | None = None,
        embedding_model: str | None = None,
        vector_size: int | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.embedding_client = embedding_client
        self.qdrant_client = qdrant_client
        self.collection_name = collection_name or settings.QDRANT_COLLECTION_DDR_TIME_LOGS
        self.embedding_model = embedding_model or settings.GEMINI_EMBEDDING_MODEL
        self.vector_size = vector_size or settings.GEMINI_EMBEDDING_DIMENSION
        self.logger = logger or logging.getLogger(__name__)

    async def embed_successful_date(self, ddr_date: Any) -> None:
        try:
            rows = self._time_log_points(ddr_date)
            if not rows:
                return
            contents = [row["text"] for row in rows]
            vectors = await self._resolve_embedding_client().embed_content(
                model=self.embedding_model,
                contents=contents,
            )
            points = [
                {
                    "id": row["id"],
                    "vector": vector,
                    "payload": row["payload"],
                }
                for row, vector in zip(rows, vectors, strict=True)
            ]
            if not points:
                return
            qdrant = self._resolve_qdrant_client()
            await qdrant.ensure_collection(collection_name=self.collection_name, vector_size=self.vector_size)
            await qdrant.upsert(collection_name=self.collection_name, points=points)
        except Exception as exc:
            self.logger.warning(
                "time_log_embedding_failed ddr_id=%s ddr_date_id=%s date=%s error=%s",
                getattr(ddr_date, "ddr_id", None),
                getattr(ddr_date, "id", None),
                getattr(ddr_date, "date", None),
                str(exc),
            )

    def _time_log_points(self, ddr_date: Any) -> list[dict[str, Any]]:
        final_json = getattr(ddr_date, "final_json", None)
        if not isinstance(final_json, dict):
            return []
        time_logs = final_json.get("time_logs")
        if not isinstance(time_logs, list):
            return []
        points = []
        for index, row in enumerate(time_logs):
            if not isinstance(row, dict):
                continue
            text = self._embedding_text(row)
            if not text:
                continue
            points.append(
                {
                    "id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"{ddr_date.id}:{index}")),
                    "text": text,
                    "payload": self._payload(ddr_date, row),
                }
            )
        return points

    def _embedding_text(self, row: dict[str, Any]) -> str:
        parts = [
            str(row.get("details") or "").strip(),
            str(row.get("activity") or "").strip(),
            str(row.get("comment") or "").strip(),
        ]
        return " ".join(part for part in parts if part)

    def _payload(self, ddr_date: Any, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "ddr_id": getattr(ddr_date, "ddr_id", None),
            "date": getattr(ddr_date, "date", None),
            "time_from": row.get("time_from") or row.get("start_time"),
            "time_to": row.get("time_to") or row.get("end_time"),
            "code": row.get("code"),
        }

    def _resolve_embedding_client(self) -> EmbeddingClientProtocol:
        if self.embedding_client is None:
            if not settings.GEMINI_API_KEY:
                raise ValueError("gemini_api_key_missing")
            self.embedding_client = GoogleEmbeddingClient(settings.GEMINI_API_KEY)
        return self.embedding_client

    def _resolve_qdrant_client(self) -> QdrantClientProtocol:
        if self.qdrant_client is None:
            api_key = settings.QDRANT_API_KEY.get_secret_value() if settings.QDRANT_API_KEY else None
            self.qdrant_client = QdrantTimeLogClient(url=settings.QDRANT_URL, api_key=api_key)
        return self.qdrant_client
