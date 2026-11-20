import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from decimal import Decimal
from typing import Any

from sqlalchemy import insert, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base  # noqa: F401 - asegura inicialización de Base antes de models
from app.modules.sales.models import Payment, Sale, SaleItem


class SalesRepository:
    """Repositorio de ventas, líneas y pagos bajo contexto transaccional RLS."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[None]:
        """Usa savepoint si ya hay una transacción activa en la sesión, o abre una nueva."""
        if self._session.in_transaction():
            async with self._session.begin_nested():
                yield
        else:
            async with self._session.begin():
                yield

    _transaction = transaction

    async def get_sale_by_client_id(
        self,
        *,
        business_id: uuid.UUID,
        client_id: uuid.UUID,
    ) -> tuple[Sale, list[SaleItem], list[Payment]] | None:
        """Obtiene una venta existente por (business_id, client_id) con líneas y pagos ordenados."""
        sale_stmt = select(Sale).where(
            Sale.business_id == business_id,
            Sale.client_id == client_id,
        )
        sale = (await self._session.execute(sale_stmt)).scalar_one_or_none()
        if sale is None:
            return None

        items_stmt = (
            select(SaleItem)
            .where(
                SaleItem.business_id == business_id,
                SaleItem.sale_id == sale.id,
            )
            .order_by(SaleItem.created_at.asc(), SaleItem.id.asc())
        )
        items = list((await self._session.execute(items_stmt)).scalars().all())

        payments_stmt = (
            select(Payment)
            .where(
                Payment.business_id == business_id,
                Payment.sale_id == sale.id,
            )
            .order_by(Payment.created_at.asc(), Payment.id.asc())
        )
        payments = list((await self._session.execute(payments_stmt)).scalars().all())

        return sale, items, payments

    async def try_insert_sale_header(
        self,
        *,
        business_id: uuid.UUID,
        client_id: uuid.UUID,
        total_amount: Decimal,
    ) -> Sale | None:
        """Inserta la cabecera de venta de forma idempotente; retorna None si hay conflicto."""
        stmt = (
            pg_insert(Sale)
            .values(
                business_id=business_id,
                client_id=client_id,
                total_amount=total_amount,
            )
            .on_conflict_do_nothing(index_elements=["business_id", "client_id"])
            .returning(Sale)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def insert_sale_items(
        self,
        *,
        items: list[dict[str, Any]],
    ) -> list[SaleItem]:
        """Inserta líneas de venta en lote y las retorna ordenadas por (created_at, id)."""
        if not items:
            return []
        stmt = insert(SaleItem).values(items).returning(SaleItem)
        rows = list((await self._session.execute(stmt)).scalars().all())
        return sorted(rows, key=lambda row: (row.created_at, row.id))

    async def insert_payments(
        self,
        *,
        payments: list[dict[str, Any]],
    ) -> list[Payment]:
        """Inserta pagos de venta en lote y los retorna ordenados por (created_at, id)."""
        if not payments:
            return []
        stmt = insert(Payment).values(payments).returning(Payment)
        rows = list((await self._session.execute(stmt)).scalars().all())
        return sorted(rows, key=lambda row: (row.created_at, row.id))
