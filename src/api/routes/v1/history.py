from typing import Annotated

from fastapi import APIRouter, Depends, Query

from src.api.dependencies.repository import get_repository
from src.models.schemas.occurrence import HistoryOccurrenceInResponse
from src.repository.crud.occurrence import OccurrenceCRUDRepository
from src.securities.authorizations.jwt_authentication import jwt_authentication

router = APIRouter(prefix="/history", tags=["History"])


@router.get("/occurrences", response_model=list[HistoryOccurrenceInResponse])
async def search_occurrence_history(
    type_filter: Annotated[list[str] | None, Query(alias="type")] = None,
    section: Annotated[list[str] | None, Query()] = None,
    operator: Annotated[list[str] | None, Query()] = None,
    depth_from: float | None = None,
    depth_to: float | None = None,
    date_from: Annotated[str | None, Query(pattern=r"^\d{8}$")] = None,
    date_to: Annotated[str | None, Query(pattern=r"^\d{8}$")] = None,
    limit: Annotated[int, Query(ge=1, le=10000)] = 1000,
    offset: Annotated[int, Query(ge=0)] = 0,
    current_user = Depends(jwt_authentication),
    occurrence_repository: OccurrenceCRUDRepository = Depends(get_repository(OccurrenceCRUDRepository)),
) -> list[HistoryOccurrenceInResponse]:
    rows = await occurrence_repository.search_history(
        type_filters=type_filter,
        section_filters=section,
        operator_filters=operator,
        depth_from=depth_from,
        depth_to=depth_to,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    return [HistoryOccurrenceInResponse.model_validate(row) for row in rows]
