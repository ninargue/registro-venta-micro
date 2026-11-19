import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from decimal import Decimal

from sqlalchemy import ColumnElement, func, insert, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base  # noqa: F401 - asegura inicialización de Base antes de models
from app.modules.catalog.models import Product


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
