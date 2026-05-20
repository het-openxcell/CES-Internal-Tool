import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse, StreamingResponse

from src.api.dependencies.repository import get_repository
from src.repository.crud.correction import CorrectionCRUDRepository
from src.repository.crud.ddr import DDRCRUDRepository, DDRDateCRUDRepository
from src.repository.crud.occurrence import OccurrenceCRUDRepository
from src.securities.authorizations.jwt_authentication import jwt_authentication
from src.services.export.csv_timelogs import TimeLogCSVExportService
from src.services.export.excel_master import MasterExcelExportService
from src.services.export.excel_report import DDRExcelExportService

router = APIRouter(prefix="/export", tags=["Export"])


@router.get("/ddr/{ddr_id}")
async def export_ddr_excel(
    ddr_id: str,
    current_user=Depends(jwt_authentication),
    ddr_repository: DDRCRUDRepository = Depends(get_repository(DDRCRUDRepository)),
    occurrence_repository: OccurrenceCRUDRepository = Depends(get_repository(OccurrenceCRUDRepository)),
    correction_repository: CorrectionCRUDRepository = Depends(get_repository(CorrectionCRUDRepository)),
) -> StreamingResponse:
    ddr = await ddr_repository.read_by_id(ddr_id)
    if ddr is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "DDR not found", "code": "NOT_FOUND", "details": {}},
        )
    occurrences = await occurrence_repository.get_by_ddr_id_filtered(ddr_id=ddr_id, limit=10000)
    corrections = await correction_repository.get_by_ddr_id(ddr_id=ddr_id, limit=10000)
    service = DDRExcelExportService()
    ddr_label = ddr.file_path.split("/")[-1]
    buf = await asyncio.to_thread(service.generate, occurrences, corrections, ddr_label)
    filename = f"{ddr_id}_occurrences.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/master")
async def export_master_excel(
    type_filter: Annotated[str | None, Query(alias="type")] = None,
    ddr_id: str | None = None,
    date_from: Annotated[str | None, Query(pattern=r"^\d{8}$")] = None,
    date_to: Annotated[str | None, Query(pattern=r"^\d{8}$")] = None,
    current_user=Depends(jwt_authentication),
    occurrence_repository: OccurrenceCRUDRepository = Depends(get_repository(OccurrenceCRUDRepository)),
) -> StreamingResponse:
    rows = await occurrence_repository.get_all_with_ddr_source(
        type_filter=type_filter,
        ddr_id=ddr_id,
        date_from=date_from,
        date_to=date_to,
        limit=50000,
    )
    has_filters = any([type_filter, ddr_id, date_from, date_to])
    filename = "occurrences_filtered.xlsx" if has_filters else "occurrences_all.xlsx"
    service = MasterExcelExportService()
    buf = await asyncio.to_thread(service.generate, rows)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/timelogs/{ddr_id}")
async def export_timelogs_csv(
    ddr_id: str,
    current_user=Depends(jwt_authentication),
    ddr_repository: DDRCRUDRepository = Depends(get_repository(DDRCRUDRepository)),
    ddr_date_repository: DDRDateCRUDRepository = Depends(get_repository(DDRDateCRUDRepository)),
) -> StreamingResponse:
    ddr = await ddr_repository.read_by_id(ddr_id)
    if ddr is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "DDR not found", "code": "NOT_FOUND", "details": {}},
        )
    dates = await ddr_date_repository.get_dates_with_timelogs(ddr_id)
    if not dates:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "Well data not found", "code": "NOT_FOUND", "details": {}},
        )
    ddr_dates_data = [{"date": d.date, "time_logs": d.final_json.get("time_logs", [])} for d in dates]
    service = TimeLogCSVExportService()
    buf = await asyncio.to_thread(service.generate, ddr_dates_data)
    filename = f"{ddr_id}_timelogs.csv"
    return StreamingResponse(
        buf,
        media_type="text/csv; charset=utf-8-sig",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
