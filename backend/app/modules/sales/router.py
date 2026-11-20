from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_tenant_db
from app.core.schemas import ErrorResponse
from app.core.security import CurrentUser, get_current_tenant
from app.modules.catalog.repository import CatalogRepository
from app.modules.catalog.service import CatalogService
from app.modules.sales.repository import SalesRepository
from app.modules.sales.schemas import SaleCreate, SaleResponse
from app.modules.sales.service import (
    SaleIdConflictError,
    SalePaymentMismatchError,
    SaleProductInactiveError,
    SaleProductNotFoundError,
    SalesService,
    SaleStockOverflowError,
    SaleTotalInvalidError,
)

router = APIRouter(prefix="/sales", tags=["sales"])


def get_sales_service(
    db: AsyncSession = Depends(get_tenant_db),
) -> SalesService:
    """Construye SalesService con repositorio de ventas y CatalogService sobre la misma sesión."""
    return SalesService(
        repository=SalesRepository(db),
        catalog_service=CatalogService(repository=CatalogRepository(db)),
    )


@router.post(
    "",
    response_model=SaleResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        200: {
            "model": SaleResponse,
            "description": "Idempotent retry returning previously persisted sale",
        },
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
async def create_sale(
    payload: SaleCreate,
    response: Response,
    current_user: CurrentUser = Depends(get_current_tenant),
    service: SalesService = Depends(get_sales_service),
) -> SaleResponse:
    """Registra una venta de forma transaccional e idempotente para el comercio autenticado."""
    try:
        sale, created = await service.create_sale(current_user, payload)
    except SaleProductNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "PRODUCT_NOT_FOUND",
                "message": "One or more products were not found",
                "details": {
                    "missing_product_ids": [str(pid) for pid in exc.missing_product_ids],
                },
            },
        ) from exc
    except SaleProductInactiveError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "PRODUCT_INACTIVE",
                "message": "Inactive products cannot be sold",
                "details": {
                    "inactive_product_ids": [str(pid) for pid in exc.inactive_product_ids],
                },
            },
        ) from exc
    except SalePaymentMismatchError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "PAYMENT_TOTAL_MISMATCH",
                "message": "Sum of payments must match server-calculated sale total",
                "details": {
                    "expected_total": str(exc.expected_total),
                    "payments_total": str(exc.payments_total),
                },
            },
        ) from exc
    except SaleIdConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "SALE_ID_CONFLICT",
                "message": "client_id already exists with different sale items or payments",
                "details": {"client_id": str(exc.client_id)},
            },
        ) from exc
    except (SaleTotalInvalidError, SaleStockOverflowError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "VALIDATION_ERROR",
                "message": str(exc),
                "details": None,
            },
        ) from exc

    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return sale
