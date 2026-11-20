from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.db import get_tenant_db
from app.core.schemas import ErrorResponse
from app.core.security import CurrentUser, require_owner
from app.modules.reports.repository import ReportsRepository
from app.modules.reports.schemas import DailyReportQuery, DailyReportResponse
from app.modules.reports.service import BusinessNotFoundError, ReportsService

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get(
    "/daily",
    response_model=DailyReportResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
async def get_daily_report(
    query: Annotated[DailyReportQuery, Query()],
    current_user: CurrentUser = Depends(require_owner),
) -> DailyReportResponse:
    """Obtiene el consolidado diario de ventas, medios de pago, costos y margen (solo owner)."""
    async for db in get_tenant_db(current_user):
        service = ReportsService(repository=ReportsRepository(db))
        try:
            return await service.get_daily_report(current_user, query.date)
        except BusinessNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "BUSINESS_NOT_FOUND",
                    "message": "Business not found",
                    "details": None,
                },
            ) from exc
    raise RuntimeError("Tenant database session was not yielded")
