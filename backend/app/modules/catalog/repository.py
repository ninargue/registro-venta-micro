import uuid
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from decimal import Decimal
from typing import Any

from sqlalchemy import ColumnElement, Numeric, case, func, insert, literal, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base  # noqa: F401 - asegura inicialización de Base antes de models
from app.modules.catalog.models import Product
from app.modules.catalog.schemas import UPDATABLE_PRODUCT_FIELDS


class CatalogRepository:
    """Repositorio de productos del catálogo bajo contexto transaccional RLS."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @asynccontextmanager
    async def _transaction(self) -> AsyncIterator[None]:
        """Usa savepoint si ya hay una transacción activa en la sesión, o abre una nueva."""
        if self._session.in_transaction():
            async with self._session.begin_nested():
                yield
        else:
            async with self._session.begin():
                yield

    async def create_product(
        self,
        *,
        business_id: uuid.UUID,
        code: str | None,
        name: str,
        sale_price: Decimal,
        cost_price: Decimal,
        stock: Decimal,
    ) -> Product:
        """Inserta un nuevo producto asociado al business_id del tenant."""
        stmt = (
            insert(Product)
            .values(
                business_id=business_id,
                code=code,
                name=name,
                sale_price=sale_price,
                cost_price=cost_price,
                stock=stock,
            )
            .returning(Product)
        )
        async with self._transaction():
            result = await self._session.execute(stmt)
            return result.scalar_one()

    async def update_product(
        self,
        *,
        product_id: uuid.UUID,
        business_id: uuid.UUID,
        updates: Mapping[str, Any],
    ) -> Product | None:
        """Actualiza parcialmente un producto del tenant bajo savepoint y retorna la fila o None."""
        if not updates:
            raise ValueError("At least one editable field must be provided")
        invalid_fields = set(updates.keys()) - UPDATABLE_PRODUCT_FIELDS
        if invalid_fields:
            raise ValueError(f"Non-updatable fields are not allowed: {sorted(invalid_fields)}")

        stmt = (
            update(Product)
            .where(Product.id == product_id, Product.business_id == business_id)
            .values(**dict(updates))
            .returning(Product)
        )
        async with self._transaction():
            result = await self._session.execute(stmt)
            return result.scalar_one_or_none()

    async def list_products(
        self,
        *,
        q: str | None,
        include_inactive: bool,
        limit: int,
        offset: int,
    ) -> tuple[list[Product], int]:
        """Lista productos paginados con filtros compartidos y orden determinista."""
        filters: list[ColumnElement[bool]] = []
        if not include_inactive:
            filters.append(Product.is_active.is_(True))
        if q:
            escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            pattern = f"%{escaped}%"
            filters.append(
                or_(
                    Product.name.ilike(pattern, escape="\\"),
                    Product.code.ilike(pattern, escape="\\"),
                )
            )

        count_stmt = select(func.count(Product.id)).where(*filters)
        total = int((await self._session.execute(count_stmt)).scalar_one())

        items_stmt = (
            select(Product)
            .where(*filters)
            .order_by(Product.name.asc(), Product.id.asc())
            .limit(limit)
            .offset(offset)
        )
        items = list((await self._session.execute(items_stmt)).scalars().all())
        return items, total

    async def lock_products_for_sale(
        self,
        *,
        business_id: uuid.UUID,
        product_ids: list[uuid.UUID],
    ) -> dict[uuid.UUID, Product]:
        """Bloquea productos del comercio en orden determinista (ORDER BY id ASC FOR UPDATE)."""
        if not product_ids:
            return {}
        ordered_ids = sorted(set(product_ids))
        stmt = (
            select(Product)
            .where(
                Product.business_id == business_id,
                Product.id.in_(ordered_ids),
            )
            .order_by(Product.id.asc())
            .with_for_update()
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return {product.id: product for product in rows}

    async def deduct_stock_batch(
        self,
        *,
        business_id: uuid.UUID,
        deductions: dict[uuid.UUID, Decimal],
    ) -> None:
        """Descuenta stock en un único UPDATE masivo con CASE WHEN filtrado por business_id."""
        if not deductions:
            return
        ordered_ids = sorted(deductions)
        deduction_case = case(
            *[
                (
                    Product.id == product_id,
                    literal(deductions[product_id], type_=Numeric(12, 2)),
                )
                for product_id in ordered_ids
            ],
            else_=literal(Decimal("0.00"), type_=Numeric(12, 2)),
        )
        stmt = (
            update(Product)
            .where(
                Product.business_id == business_id,
                Product.id.in_(ordered_ids),
            )
            .values(stock=Product.stock - deduction_case)
        )
        await self._session.execute(stmt)

    async def get_product_names_by_ids(
        self,
        *,
        business_id: uuid.UUID,
        product_ids: list[uuid.UUID],
    ) -> dict[uuid.UUID, str]:
        """Obtiene nombres de productos del comercio por sus IDs bajo contexto RLS."""
        if not product_ids:
            return {}
        unique_ids = sorted(set(product_ids))
        stmt = select(Product.id, Product.name).where(
            Product.business_id == business_id,
            Product.id.in_(unique_ids),
        )
        rows = (await self._session.execute(stmt)).all()
        return {row.id: row.name for row in rows}
