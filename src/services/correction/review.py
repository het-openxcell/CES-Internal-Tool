from src.models.schemas.correction import CorrectionPageResponse, CorrectionReviewItem
from src.repository.crud.correction import CorrectionCRUDRepository


class CorrectionReviewService:
    def __init__(self, correction_repository: CorrectionCRUDRepository) -> None:
        self.correction_repository = correction_repository

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
        return CorrectionPageResponse(
            items=[CorrectionReviewItem.model_validate(row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
        )
