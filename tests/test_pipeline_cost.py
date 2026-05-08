import asyncio
from decimal import Decimal
from types import SimpleNamespace

from src.models.schemas.ddr import DDRDateStatus
from src.repository.crud.ddr import DDRDateCRUDRepository, PipelineRunCRUDRepository
from src.services.pipeline.cost import ExtractionCostService


class FakeSession:
    def __init__(self) -> None:
        self.added = []
        self.commits = 0
        self.flushes = 0
        self.refreshes = 0

    def add(self, record) -> None:
        self.added.append(record)

    async def commit(self) -> None:
        self.commits += 1

    async def flush(self) -> None:
        self.flushes += 1

    async def refresh(self, _record) -> None:
        self.refreshes += 1


def test_cost_service_calculates_decimal_cost_to_six_places() -> None:
    service = ExtractionCostService(
        input_cost_per_1m_tokens=Decimal("0.10"),
        output_cost_per_1m_tokens=Decimal("0.40"),
    )

    cost = service.calculate_cost(input_tokens=12345, output_tokens=6789)

    assert cost == Decimal("0.003950")


def test_cost_service_persists_run_without_committing_when_requested() -> None:
    session = FakeSession()
    repository = PipelineRunCRUDRepository(session)
    service = ExtractionCostService(
        pipeline_run_repository=repository,
        input_cost_per_1m_tokens=Decimal("0.10"),
        output_cost_per_1m_tokens=Decimal("0.40"),
    )

    run = asyncio.run(
        service.record_extraction_run(
            ddr_date_id="11111111-1111-1111-1111-111111111111",
            input_tokens=10,
            output_tokens=20,
            commit=False,
        )
    )

    assert run.gemini_input_tokens == 10
    assert run.gemini_output_tokens == 20
    assert run.cost_usd == Decimal("0.000009")
    assert session.commits == 0
    assert session.flushes == 1


def test_pipeline_run_repository_aggregates_all_time_cost() -> None:
    class AggregateSession:
        async def execute(self, statement):
            assert "coalesce" in str(statement).lower()
            return SimpleNamespace(one=lambda: (Decimal("1.234567"), 3))

    result = asyncio.run(PipelineRunCRUDRepository(AggregateSession()).aggregate_all_time_cost())

    assert result.total_cost_usd == Decimal("1.234567")
    assert result.total_runs == 3


def test_mark_success_can_share_transaction_with_pipeline_run() -> None:
    session = FakeSession()
    date_repository = DDRDateCRUDRepository(session)
    run_repository = PipelineRunCRUDRepository(session)
    row = SimpleNamespace(status=DDRDateStatus.QUEUED, raw_response=None, final_json=None, error_log=None, updated_at=0)

    asyncio.run(
        date_repository.mark_success(
            row,
            raw_response={"text": "ok"},
            final_json={"time_logs": []},
            commit=False,
        )
    )
    asyncio.run(
        run_repository.create_pipeline_run(
            ddr_date_id="11111111-1111-1111-1111-111111111111",
            gemini_input_tokens=1,
            gemini_output_tokens=2,
            cost_usd=Decimal("0.000001"),
            commit=False,
        )
    )
    asyncio.run(session.commit())

    assert row.status == DDRDateStatus.SUCCESS
    assert session.flushes == 2
    assert session.commits == 1
