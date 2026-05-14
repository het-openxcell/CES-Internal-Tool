from fastapi import APIRouter, Depends, HTTPException, status

from src.securities.authorizations.jwt_authentication import jwt_authentication
from src.services.keywords.loader import KeywordLoader
from src.services.occurrence.classify import VALID_OCCURRENCE_TYPES

router = APIRouter(prefix="/keywords", tags=["Keywords"])


@router.get("", status_code=status.HTTP_200_OK)
async def get_keywords(
    current_user=Depends(jwt_authentication),
) -> dict[str, str]:
    return KeywordLoader.get_keywords()


@router.put("", status_code=status.HTTP_200_OK)
async def update_keywords(
    keywords: dict[str, str],
    current_user=Depends(jwt_authentication),
) -> dict[str, int]:
    if len(keywords) > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Too many keywords: {len(keywords)}. Maximum is 1000.",
        )
    invalid = {v for v in keywords.values() if v not in VALID_OCCURRENCE_TYPES}
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Invalid occurrence types: {sorted(invalid)}. Must be one of: {sorted(VALID_OCCURRENCE_TYPES)}",
        )
    KeywordLoader.reload(keywords)
    return {"updated": len(keywords)}
