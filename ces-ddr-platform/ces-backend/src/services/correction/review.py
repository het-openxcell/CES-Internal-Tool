from src.models.schemas.correction import CorrectionPageResponse, CorrectionReviewItem, CorrectionSummaryInResponse
from src.repository.crud.correction import CorrectionCRUDRepository
from src.repository.crud.correction_summary import CorrectionSummaryCRUDRepository


class CorrectionReviewService:
    def __init__(
        self,
        correction_repository: CorrectionCRUDRepository,
        correction_summary_repository: CorrectionSummaryCRUDRepository | None = None,
    ) -> None:
        self.correction_repository = correction_repository
        self.correction_summary_repository = correction_summary_repository

    async def list_corrections(
        self,
        field_name: str | None,
        ddr_id: str | None,
        page: int,
        page_size: int,
    ) -> CorrectionPageResponse:
        offset = (page - 1) * page_size
        rows = await self.correction_repository.get_all(
            field_name=field_name,
            ddr_id=ddr_id,
            limit=page_size,
            offset=offset,
        )
        total = await self.correction_repository.count_all(field_name=field_name, ddr_id=ddr_id)
        summaries = []
        if ddr_id is not None and self.correction_summary_repository is not None:
            summaries = await self.correction_summary_repository.get_by_ddr_id(ddr_id, limit=page_size, offset=offset)
        return CorrectionPageResponse(
            items=[CorrectionReviewItem.model_validate(row) for row in rows],
            summaries=[CorrectionSummaryInResponse.model_validate(row) for row in summaries],
            total=total,
            page=page,
            page_size=page_size,
        )
