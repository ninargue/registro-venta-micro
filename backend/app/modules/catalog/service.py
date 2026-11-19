import uuid
from decimal import Decimal

from sqlalchemy.exc import IntegrityError

from app.core.security import CurrentUser
from app.modules.catalog.models import Product
from app.modules.catalog.repository import CatalogRepository
from app.modules.catalog.schemas import (
    UPDATABLE_PRODUCT_FIELDS,
    ProductCreate,
    ProductListQuery,
    ProductListResponse,
    ProductResponse,
    ProductUpdate,
)

PRODUCT_CODE_UNIQUE_CONSTRAINT = "uq_products_business_id_code"


class DuplicateProductCodeError(Exception):
    """Error lanzado cuando ya existe un producto con el mismo código en el comercio."""


class ProductNotFoundError(Exception):
    """Error lanzado cuando el producto no existe o no pertenece al comercio autenticado."""


def _is_duplicate_product_code_violation(exc: IntegrityError) -> bool:
    orig = exc.orig
    if orig is None:
        return False
    cause = getattr(orig, "__cause__", None)
    sqlstate = (
        getattr(orig, "sqlstate", None)
        or getattr(orig, "pgcode", None)
        or getattr(cause, "sqlstate", None)
        or getattr(cause, "pgcode", None)
    )
    constraint_name = getattr(orig, "constraint_name", None) or getattr(
        cause, "constraint_name", None
    )
    return sqlstate == "23505" and (
        constraint_name == PRODUCT_CODE_UNIQUE_CONSTRAINT
        or PRODUCT_CODE_UNIQUE_CONSTRAINT in str(orig)
    )


class CatalogService:
    """Casos de uso del catálogo de productos."""

    def __init__(self, repository: CatalogRepository) -> None:
        self._repository = repository

    @staticmethod
    def _to_product_response(product: Product, *, redact_cost: bool) -> ProductResponse:
        return ProductResponse(
            id=product.id,
            code=product.code,
            name=product.name,
            sale_price=product.sale_price,
            cost_price=None if redact_cost else product.cost_price,
            stock=product.stock,
            is_active=product.is_active,
            created_at=product.created_at,
            updated_at=product.updated_at,
        )

    async def create_product(
        self,
        current_user: CurrentUser,
        payload: ProductCreate,
    ) -> ProductResponse:
        """Crea un producto asociado exclusivamente al comercio del usuario autenticado."""
        if current_user.business_id is None:
            raise ValueError("Tenant business_id is required")

        try:
            product = await self._repository.create_product(
                business_id=current_user.business_id,
                code=payload.code,
                name=payload.name,
                sale_price=payload.sale_price,
                cost_price=payload.cost_price,
                stock=payload.stock,
            )
        except IntegrityError as exc:
            if _is_duplicate_product_code_violation(exc):
                raise DuplicateProductCodeError(
                    "Product code already exists for this business"
                ) from exc
            raise

        return self._to_product_response(product, redact_cost=False)

    async def update_product(
        self,
        current_user: CurrentUser,
        product_id: uuid.UUID,
        payload: ProductUpdate,
    ) -> ProductResponse:
        """Actualiza parcialmente un producto perteneciente al comercio del usuario autenticado."""
        if current_user.business_id is None:
            raise ValueError("Tenant business_id is required")

        raw_updates = payload.model_dump(exclude_unset=True)
        updates = {
            key: value for key, value in raw_updates.items() if key in UPDATABLE_PRODUCT_FIELDS
        }

        try:
            product = await self._repository.update_product(
                product_id=product_id,
                business_id=current_user.business_id,
                updates=updates,
            )
        except IntegrityError as exc:
            if _is_duplicate_product_code_violation(exc):
                raise DuplicateProductCodeError(
                    "Product code already exists for this business"
                ) from exc
            raise

        if product is None:
            raise ProductNotFoundError("Product not found")

        return self._to_product_response(product, redact_cost=False)

    async def list_products(
        self,
        current_user: CurrentUser,
        query: ProductListQuery,
    ) -> ProductListResponse:
        """Lista productos del comercio aplicando redacción de costo para roles no owner."""
        items, total = await self._repository.list_products(
            q=query.q,
            include_inactive=query.include_inactive,
            limit=query.limit,
            offset=query.offset,
        )
        redact_cost = current_user.role != "owner"
        return ProductListResponse(
            items=[self._to_product_response(item, redact_cost=redact_cost) for item in items],
            total=total,
            limit=query.limit,
            offset=query.offset,
        )

    async def lock_products_for_sale(
        self,
        *,
        business_id: uuid.UUID,
        product_ids: list[uuid.UUID],
    ) -> dict[uuid.UUID, Product]:
        """Bloquea y devuelve los productos del comercio en orden determinista para una venta."""
        return await self._repository.lock_products_for_sale(
            business_id=business_id,
            product_ids=product_ids,
        )

    async def deduct_stock_batch(
        self,
        *,
        business_id: uuid.UUID,
        deductions: dict[uuid.UUID, Decimal],
    ) -> None:
        """Descuenta stock por lote del comercio dentro de la transacción activa."""
        await self._repository.deduct_stock_batch(
            business_id=business_id,
            deductions=deductions,
        )

    async def get_product_names_by_ids(
        self,
        *,
        business_id: uuid.UUID,
        product_ids: list[uuid.UUID],
    ) -> dict[uuid.UUID, str]:
        """Devuelve un mapa product_id -> name del comercio para armar comprobantes."""
        return await self._repository.get_product_names_by_ids(
            business_id=business_id,
            product_ids=product_ids,
        )
