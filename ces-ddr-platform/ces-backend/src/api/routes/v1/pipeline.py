from fastapi import APIRouter, Depends

from src.api.dependencies.repository import get_repository
from src.repository.crud.ddr import PipelineRunCRUDRepository
from src.securities.authorizations.jwt_authentication import jwt_authentication
from src.services.pipeline.cost import ExtractionCostService

router = APIRouter(prefix="/pipeline", tags=["Pipeline"])


@router.get("/cost")
async def get_pipeline_cost(
    current_user = Depends(jwt_authentication),
    pipeline_run_repository: PipelineRunCRUDRepository = Depends(get_repository(PipelineRunCRUDRepository)),
) -> dict[str, float | int | str]:
    service = ExtractionCostService(pipeline_run_repository=pipeline_run_repository)
    aggregate = await service.aggregate_all_time_cost()
    return {
        "total_cost_usd": str(aggregate.total_cost_usd),
        "total_runs": aggregate.total_runs,
        "period": "all_time",
    }
