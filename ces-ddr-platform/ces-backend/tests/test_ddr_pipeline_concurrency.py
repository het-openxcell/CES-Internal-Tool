import asyncio

import pytest

import src.services.ddr as ddr_module
from src.config.manager import settings
from src.services.ddr import DDRProcessingTask, DDRReprocessTask


class ConcurrencySessionFactory:
    """Fake session_factory that tracks how many sessions are open at once.

    A DDR pipeline run holds its DB session for the entire run, so counting
    concurrently-open sessions is equivalent to counting concurrently-running
    pipelines — exactly the resource the DB_POOL_SIZE/overflow limit protects.
    """

    def __init__(self) -> None:
        self.active = 0
        self.max_active = 0
        self._lock = asyncio.Lock()

    def __call__(self):
        return self._SessionCM(self)

    class _SessionCM:
        def __init__(self, outer: "ConcurrencySessionFactory") -> None:
            self._outer = outer

        async def __aenter__(self) -> "FakeAsyncSession":
            async with self._outer._lock:
                self._outer.active += 1
                self._outer.max_active = max(self._outer.max_active, self._outer.active)
            return FakeAsyncSession()

        async def __aexit__(self, exc_type, exc, tb) -> bool:
            async with self._outer._lock:
                self._outer.active -= 1
            return False


class FakeAsyncSession:
    async def execute(self, *args, **kwargs):
        return None

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


class SlowFakePipelineService:
    """Stands in for PreSplitPipelineService; just holds the session slot briefly."""

    def __init__(self, delay: float = 0.05) -> None:
        self.status_stream_service = None
        self._delay = delay

    async def run(self, ddr_id: str) -> None:
        await asyncio.sleep(self._delay)

    async def reprocess_full(self, ddr_id: str) -> None:
        await asyncio.sleep(self._delay)

    async def reprocess_dates(self, ddr_id: str, dates) -> None:
        await asyncio.sleep(self._delay)


@pytest.fixture(autouse=True)
def reset_shared_pipeline_semaphore(monkeypatch):
    """Fresh global pipeline semaphore per test so runs don't leak state."""
    monkeypatch.setattr(ddr_module, "_shared_pipeline_semaphore", None)
    yield
    monkeypatch.setattr(ddr_module, "_shared_pipeline_semaphore", None)


def test_concurrent_uploads_never_exceed_global_pipeline_cap(monkeypatch):
    """
    Reproduces the client-reported bug: uploading many files at once used to let
    every one of them open a DB session and run its full pipeline simultaneously,
    starving the small DB_POOL_SIZE/overflow pool and making list/monitor endpoints
    time out. Concurrent pipeline runs must now be capped at DDR_PIPELINE_MAX_CONCURRENT.
    """
    monkeypatch.setattr(settings, "DDR_PIPELINE_MAX_CONCURRENT", 2)

    session_factory = ConcurrencySessionFactory()
    fake_service = SlowFakePipelineService()

    def pipeline_service_factory(session):
        return fake_service

    tasks = [
        DDRProcessingTask(
            session_factory=session_factory,
            pipeline_service_factory=pipeline_service_factory,
        )
        for _ in range(8)
    ]

    async def run_all():
        await asyncio.gather(*[task.process(f"ddr-{i}") for i, task in enumerate(tasks)])

    asyncio.run(run_all())

    assert session_factory.max_active <= 2, (
        f"expected global cap of 2 concurrent pipeline sessions, "
        f"observed {session_factory.max_active} — pipeline concurrency is not gated"
    )


def test_explicit_max_concurrent_gets_isolated_semaphore(monkeypatch):
    """A caller passing max_concurrent explicitly must not share the global cap."""
    monkeypatch.setattr(settings, "DDR_PIPELINE_MAX_CONCURRENT", 1)

    session_factory = ConcurrencySessionFactory()
    fake_service = SlowFakePipelineService()

    def pipeline_service_factory(session):
        return fake_service

    # One task instance, explicit max_concurrent=3, fed 6 concurrent ddr_ids —
    # its own cap must be honored regardless of the global default of 1.
    task = DDRProcessingTask(
        session_factory=session_factory,
        pipeline_service_factory=pipeline_service_factory,
        max_concurrent=3,
    )

    async def run_all():
        await asyncio.gather(*[task.process(f"ddr-{i}") for i in range(6)])

    asyncio.run(run_all())

    assert session_factory.max_active <= 3
    assert session_factory.max_active > 1, (
        "explicit max_concurrent=3 should not be clamped down to the global default of 1"
    )


def test_uploads_and_reprocesses_share_the_same_global_cap(monkeypatch):
    """
    The client's report involved fresh uploads AND reprocesses of failed reports
    getting stuck at the same time. Both paths draw from the same DB pool, so they
    must share one global pipeline semaphore, not get independent budgets that
    together exceed the pool.
    """
    monkeypatch.setattr(settings, "DDR_PIPELINE_MAX_CONCURRENT", 2)

    session_factory = ConcurrencySessionFactory()
    fake_service = SlowFakePipelineService()

    def pipeline_service_factory(session):
        return fake_service

    processing_tasks = [
        DDRProcessingTask(
            session_factory=session_factory,
            pipeline_service_factory=pipeline_service_factory,
        )
        for _ in range(4)
    ]
    reprocess_tasks = [
        DDRReprocessTask(
            session_factory=session_factory,
            pipeline_service_factory=pipeline_service_factory,
        )
        for _ in range(4)
    ]

    async def run_all():
        await asyncio.gather(
            *[t.process(f"upload-{i}") for i, t in enumerate(processing_tasks)],
            *[t.full(f"reprocess-{i}") for i, t in enumerate(reprocess_tasks)],
        )

    asyncio.run(run_all())

    assert session_factory.max_active <= 2, (
        f"expected uploads+reprocesses combined to respect the global cap of 2, "
        f"observed {session_factory.max_active}"
    )
