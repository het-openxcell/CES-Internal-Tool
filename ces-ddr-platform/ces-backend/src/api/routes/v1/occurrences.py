from fastapi import APIRouter, Depends, status

from src.api.dependencies.services import get_occurrence_correction_service
from src.models.schemas.occurrence import OccurrenceCorrectionRequest, OccurrenceInResponse
from src.securities.authorizations.jwt_authentication import jwt_authentication
from src.services.ddr import OccurrenceCorrectionService

router = APIRouter(prefix="/occurrences", tags=["Occurrences"])


@router.patch("/{occurrence_id}", response_model=OccurrenceInResponse, status_code=status.HTTP_200_OK)
async def patch_occurrence(
    occurrence_id: str,
    payload: OccurrenceCorrectionRequest,
    current_user=Depends(jwt_authentication),
    service: OccurrenceCorrectionService = Depends(get_occurrence_correction_service),
) -> OccurrenceInResponse:
    occurrence = await service.patch_occurrence(
        occurrence_id=occurrence_id,
        field_name=payload.field_name,
        corrected_value=payload.corrected_value,
        reason=payload.reason,
        current_user=current_user,
    )
    return OccurrenceInResponse.model_validate(occurrence)
