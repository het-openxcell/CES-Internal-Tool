from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from src.config.manager import settings
from src.constants.cost import COST_QUANTUM, TOKEN_UNIT
from src.repository.crud.ddr import PipelineRunCRUDRepository


class ExtractionCostService:
    def __init__(
        self,
        pipeline_run_repository: PipelineRunCRUDRepository | None = None,
        input_cost_per_1m_tokens: Decimal | None = None,
        output_cost_per_1m_tokens: Decimal | None = None,
    ) -> None:
        self.pipeline_run_repository = pipeline_run_repository
        self.input_cost_per_1m_tokens = input_cost_per_1m_tokens or Decimal(
            settings.GEMINI_FLASH_LITE_INPUT_COST_PER_1M_TOKENS
        )
        self.output_cost_per_1m_tokens = output_cost_per_1m_tokens or Decimal(
            settings.GEMINI_FLASH_LITE_OUTPUT_COST_PER_1M_TOKENS
        )

    def calculate_cost(self, input_tokens: int | None, output_tokens: int | None) -> Decimal:
        input_cost = (Decimal(input_tokens or 0) / TOKEN_UNIT) * self.input_cost_per_1m_tokens
        output_cost = (Decimal(output_tokens or 0) / TOKEN_UNIT) * self.output_cost_per_1m_tokens
        return (input_cost + output_cost).quantize(COST_QUANTUM, rounding=ROUND_HALF_UP)

    async def record_extraction_run(
        self,
        *,
        ddr_date_id: str,
        input_tokens: int | None,
        output_tokens: int | None,
        commit: bool = True,
    ) -> Any:
        if self.pipeline_run_repository is None:
            raise ValueError("pipeline_run_repository_required")
        cost_usd = self.calculate_cost(input_tokens=input_tokens, output_tokens=output_tokens)
        return await self.pipeline_run_repository.create_pipeline_run(
            ddr_date_id=ddr_date_id,
            gemini_input_tokens=input_tokens,
            gemini_output_tokens=output_tokens,
            cost_usd=cost_usd,
            commit=commit,
        )

    async def aggregate_all_time_cost(self) -> Any:
        if self.pipeline_run_repository is None:
            raise ValueError("pipeline_run_repository_required")
        return await self.pipeline_run_repository.aggregate_all_time_cost()
