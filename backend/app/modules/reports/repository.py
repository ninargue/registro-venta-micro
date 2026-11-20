import datetime as dt
import uuid
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import Date, bindparam, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True, slots=True)
class DailySalesAggregate:
    """Resultado agregado crudo del consolidado diario desde PostgreSQL."""

    report_date: dt.date
    timezone: str
    transactions_count: int
    total_sales: Decimal
    raw_total_cost: Decimal
    cash_total: Decimal
    card_total: Decimal
    transfer_total: Decimal


_DAILY_REPORT_SQL = text(
    """
    WITH target_business AS (
        SELECT
            b.id AS business_id,
            b.timezone AS timezone,
            COALESCE(
                :report_date,
                (now() AT TIME ZONE b.timezone)::date
            ) AS report_date
        FROM businesses b
        WHERE b.id = :business_id
    ),
    day_bounds AS (
        SELECT
            tb.business_id,
            tb.timezone,
            tb.report_date,
            (tb.report_date::timestamp AT TIME ZONE tb.timezone) AS start_utc,
            ((tb.report_date + 1)::timestamp AT TIME ZONE tb.timezone) AS end_utc
        FROM target_business tb
    ),
    filtered_sales AS (
        SELECT
            s.id,
            s.business_id,
            s.total_amount
        FROM sales s
        CROSS JOIN day_bounds db
        WHERE s.business_id = db.business_id
          AND s.created_at >= (db.start_utc - interval '2 hours')
          AND s.created_at < (db.end_utc + interval '2 hours')
          AND (s.created_at AT TIME ZONE db.timezone)::date = db.report_date
    ),
    sales_agg AS (
        SELECT
            COUNT(fs.id)::integer AS transactions_count,
            COALESCE(SUM(fs.total_amount), 0) AS total_sales
        FROM filtered_sales fs
    ),
    items_agg AS (
        SELECT
            COALESCE(SUM(si.quantity * si.unit_cost), 0) AS raw_total_cost
        FROM sale_items si
        INNER JOIN filtered_sales fs
            ON fs.business_id = si.business_id
           AND fs.id = si.sale_id
    ),
    payments_agg AS (
        SELECT
            COALESCE(
                SUM(CASE WHEN p.payment_method = 'cash' THEN p.amount ELSE 0 END),
                0
            ) AS cash_total,
            COALESCE(
                SUM(CASE WHEN p.payment_method = 'card' THEN p.amount ELSE 0 END),
                0
            ) AS card_total,
            COALESCE(
                SUM(CASE WHEN p.payment_method = 'transfer' THEN p.amount ELSE 0 END),
                0
            ) AS transfer_total
        FROM payments p
        INNER JOIN filtered_sales fs
            ON fs.business_id = p.business_id
           AND fs.id = p.sale_id
    )
    SELECT
        db.report_date,
        db.timezone,
        sa.transactions_count,
        sa.total_sales,
        ia.raw_total_cost,
        pa.cash_total,
        pa.card_total,
        pa.transfer_total
    FROM day_bounds db
    CROSS JOIN sales_agg sa
    CROSS JOIN items_agg ia
    CROSS JOIN payments_agg pa
    """
).bindparams(
    bindparam("business_id", type_=PG_UUID(as_uuid=True)),
    bindparam("report_date", type_=Date()),
)


class ReportsRepository:
    """Repositorio de lectura analítica de reportes bajo sesión RLS."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_daily_aggregate(
        self,
        *,
        business_id: uuid.UUID,
        report_date: dt.date | None,
    ) -> DailySalesAggregate | None:
        """Agrega ventas, costos y pagos del día local sin fan-out bajo RLS."""
        result = await self._session.execute(
            _DAILY_REPORT_SQL,
            {"business_id": business_id, "report_date": report_date},
        )
        row = result.mappings().one_or_none()
        if row is None:
            return None

        return DailySalesAggregate(
            report_date=row["report_date"],
            timezone=row["timezone"],
            transactions_count=int(row["transactions_count"]),
            total_sales=Decimal(row["total_sales"]),
            raw_total_cost=Decimal(row["raw_total_cost"]),
            cash_total=Decimal(row["cash_total"]),
            card_total=Decimal(row["card_total"]),
            transfer_total=Decimal(row["transfer_total"]),
        )
