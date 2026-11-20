import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_tenant_db
from app.core.schemas import ErrorResponse
from app.core.security import CurrentUser, get_current_tenant, require_owner
from app.modules.catalog.repository import CatalogRepository
from app.modules.catalog.schemas import (
    ProductCreate,
    ProductListQuery,
    ProductListResponse,
    ProductResponse,
    ProductUpdate,
)
from app.modules.catalog.service import (
    CatalogService,
    DuplicateProductCodeError,
    ProductNotFoundError,
)

router = APIRouter(prefix="/catalog", tags=["catalog"])


def get_catalog_service(
    db: AsyncSession = Depends(get_tenant_db),
) -> CatalogService:
    """Construye CatalogService con sesión transaccional RLS del comercio."""
    return CatalogService(repository=CatalogRepository(db))


@router.get(
    "/products",
    response_model=ProductListResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
async def list_products(
    query: Annotated[ProductListQuery, Query()],
    current_user: CurrentUser = Depends(get_current_tenant),
    service: CatalogService = Depends(get_catalog_service),
) -> ProductListResponse:
    """Lista productos del catálogo del comercio autenticado con búsqueda y paginación."""
    return await service.list_products(current_user, query)


@router.post(
    "/products",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
async def create_product(
    payload: ProductCreate,
    current_user: CurrentUser = Depends(require_owner),
    service: CatalogService = Depends(get_catalog_service),
) -> ProductResponse:
    """Crea un producto en el catálogo del comercio autenticado (solo owner)."""
    try:
        return await service.create_product(current_user, payload)
    except DuplicateProductCodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "PRODUCT_CODE_ALREADY_EXISTS",
                "message": "A product with this code already exists",
                "details": None,
            },
        ) from exc


@router.patch(
    "/products/{product_id}",
    response_model=ProductResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
async def update_product(
    product_id: uuid.UUID,
    payload: ProductUpdate,
    current_user: CurrentUser = Depends(require_owner),
    service: CatalogService = Depends(get_catalog_service),
) -> ProductResponse:
    """Actualiza parcialmente un producto del catálogo del comercio autenticado (solo owner)."""
    try:
        return await service.update_product(current_user, product_id, payload)
    except ProductNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "PRODUCT_NOT_FOUND",
                "message": "Product not found",
                "details": None,
            },
        ) from exc
    except DuplicateProductCodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "PRODUCT_CODE_ALREADY_EXISTS",
                "message": "A product with this code already exists",
                "details": None,
            },
        ) from exc
