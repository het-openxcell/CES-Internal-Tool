from fastapi import APIRouter, Depends, HTTPException
from src.utilities.logging.logger import logger

from src.models.schemas.query import NLQueryRequest, NLQueryResponse, TimeLogSource
from src.securities.authorizations.jwt_authentication import jwt_authentication
from src.services.query import NaturalLanguageQueryService

router = APIRouter(prefix="/query", tags=["Query"])


@router.post("/nl", response_model=NLQueryResponse)
async def natural_language_query(
    body: NLQueryRequest,
    current_user=Depends(jwt_authentication),
) -> NLQueryResponse:
    if not body.query.strip():
        raise HTTPException(status_code=422, detail="Query cannot be empty")

    try:
        answer, hits, expanded = await NaturalLanguageQueryService().answer(body.query)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"nl_query_unexpected_error error={exc}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred. Please try again.")
    sources = [
        TimeLogSource(
            ddr_id=(hit.get("payload") or {}).get("ddr_id"),
            date=(hit.get("payload") or {}).get("date"),
            well_name=(hit.get("payload") or {}).get("well_name"),
            surface_location=(hit.get("payload") or {}).get("surface_location"),
            text=(hit.get("payload") or {}).get("text"),
            score=hit.get("score"),
        )
        for hit in hits
    ]

    return NLQueryResponse(answer=answer, sources=sources, expanded_queries=expanded)
