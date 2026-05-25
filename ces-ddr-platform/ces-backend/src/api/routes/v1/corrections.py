from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from src.api.dependencies.services import get_correction_review_service
from src.models.schemas.correction import CorrectionPageResponse
from src.securities.authorizations.jwt_authentication import jwt_authentication
from src.services.correction.review import CorrectionReviewService

router = APIRouter(prefix="/corrections", tags=["Corrections"])


@router.get("", response_model=CorrectionPageResponse, status_code=status.HTTP_200_OK)
async def get_corrections(
    field_name: str | None = Query(default=None),
    ddr_id: UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    current_user=Depends(jwt_authentication),
    service: CorrectionReviewService = Depends(get_correction_review_service),
) -> CorrectionPageResponse:
    ddr_id_value = str(ddr_id) if ddr_id is not None else None
    return await service.list_corrections(field_name=field_name, ddr_id=ddr_id_value, page=page, page_size=page_size)
