import asyncio
import uuid
from types import SimpleNamespace

from src.services.pipeline.embedding import TimeLogEmbeddingService


class FakeEmbeddingClient:
    def __init__(self) -> None:
        self.contents = []

    async def embed_content(self, *, model, contents):
        self.contents.append({"model": model, "contents": contents})
        return [[float(index)] * 4 for index, _content in enumerate(contents, start=1)]


class FakeQdrantClient:
    def __init__(self, fail_upsert: bool = False) -> None:
        self.collection_calls = []
        self.upsert_calls = []
        self.fail_upsert = fail_upsert

    async def ensure_collection(self, *, collection_name, vector_size):
        self.collection_calls.append({"collection_name": collection_name, "vector_size": vector_size})

    async def upsert(self, *, collection_name, points):
        if self.fail_upsert:
            raise RuntimeError("qdrant down")
        self.upsert_calls.append({"collection_name": collection_name, "points": points})


class FakeLogger:
    def __init__(self) -> None:
        self.warnings = []

    def warning(self, message: str) -> None:
        self.warnings.append(message)


def test_embedding_service_extracts_time_log_text_and_payloads() -> None:
    embedding_client = FakeEmbeddingClient()
    qdrant_client = FakeQdrantClient()
    service = TimeLogEmbeddingService(
        embedding_client=embedding_client,
        qdrant_client=qdrant_client,
        collection_name="ddr_time_logs",
        embedding_model="gemini-embedding-2",
        vector_size=4,
    )
    row = SimpleNamespace(
        id="date-1",
        ddr_id="ddr-1",
        date="20240115",
        final_json={
            "time_logs": [
                {
                    "start_time": "00:00",
                    "end_time": "06:00",
                    "activity": "Drill ahead",
                    "comment": "Smooth run",
                    "code": "DRL",
                },
                {"start_time": "06:00", "end_time": "07:00", "activity": "   ", "comment": ""},
                {"time_from": "07:00", "time_to": "08:00", "details": "Connection work"},
            ]
        },
    )

    asyncio.run(service.embed_successful_date(row))

    assert embedding_client.contents == [
        {
            "model": "gemini-embedding-2",
            "contents": ["Drill ahead Smooth run", "Connection work"],
        }
    ]
    assert embedding_client.contents[0]["model"] == "gemini-embedding-2"
    assert qdrant_client.collection_calls == [{"collection_name": "ddr_time_logs", "vector_size": 4}]
    points = qdrant_client.upsert_calls[0]["points"]
    assert points[0]["id"] == str(uuid.uuid5(uuid.NAMESPACE_URL, "date-1:0"))
    assert points[0]["payload"]["ddr_id"] == "ddr-1"
    assert points[0]["payload"]["date"] == "20240115"
    assert points[0]["payload"]["time_from"] == "00:00"
    assert points[0]["payload"]["time_to"] == "06:00"
    assert points[0]["payload"]["code"] == "DRL"
    assert "text" not in points[0]["payload"]
    assert points[1]["id"] == str(uuid.uuid5(uuid.NAMESPACE_URL, "date-1:2"))
    assert points[1]["payload"]["time_from"] == "07:00"
    assert points[1]["payload"]["code"] is None


def test_embedding_failure_logs_warning_without_raising() -> None:
    logger = FakeLogger()
    service = TimeLogEmbeddingService(
        embedding_client=FakeEmbeddingClient(),
        qdrant_client=FakeQdrantClient(fail_upsert=True),
        collection_name="ddr_time_logs",
        embedding_model="gemini-embedding-2",
        vector_size=4,
        service_logger=logger,
    )
    row = SimpleNamespace(
        id="date-1",
        ddr_id="ddr-1",
        date="20240115",
        final_json={"time_logs": [{"start_time": "00:00", "end_time": "06:00", "activity": "Drill ahead"}]},
    )

    asyncio.run(service.embed_successful_date(row))

    assert row.final_json["time_logs"][0]["activity"] == "Drill ahead"
    assert len(logger.warnings) == 1
    assert "time_log_embedding_failed" in logger.warnings[0]
    assert "ddr-1" in logger.warnings[0]
    assert "date-1" in logger.warnings[0]
