import datetime as dt
from decimal import ROUND_HALF_UP, Decimal

from app.core.security import CurrentUser
from app.modules.reports.repository import ReportsRepository
from app.modules.reports.schemas import (
    DECIMAL_QUANTIZER,
    PERCENT_MULTIPLIER,
    DailyReportResponse,
    PaymentMethodBreakdown,
)


class BusinessNotFoundError(Exception):
    """Error lanzado cuando el comercio autenticado no existe bajo RLS."""


class ReportsService:
    """Casos de uso de reportes analíticos del comercio."""

    def __init__(self, repository: ReportsRepository) -> None:
        self._repository = repository

    async def get_daily_report(
        self,
        current_user: CurrentUser,
        target_date: dt.date | None,
    ) -> DailyReportResponse:
        """Obtiene el consolidado diario de ventas, costos y margen bruto."""
        if current_user.business_id is None:
            raise ValueError("Tenant business_id is required")

        agg = await self._repository.get_daily_aggregate(
            business_id=current_user.business_id,
            report_date=target_date,
        )
        if agg is None:
            raise BusinessNotFoundError("Business not found")

        total_sales = agg.total_sales.quantize(DECIMAL_QUANTIZER, rounding=ROUND_HALF_UP)
        total_cost = agg.raw_total_cost.quantize(DECIMAL_QUANTIZER, rounding=ROUND_HALF_UP)
        gross_margin = (total_sales - total_cost).quantize(
            DECIMAL_QUANTIZER, rounding=ROUND_HALF_UP
        )
        margin_percentage = (
            Decimal("0.00")
            if total_sales == Decimal("0.00")
            else ((gross_margin / total_sales) * PERCENT_MULTIPLIER).quantize(
                DECIMAL_QUANTIZER, rounding=ROUND_HALF_UP
            )
        )

        payment_breakdown = PaymentMethodBreakdown(
            cash=agg.cash_total.quantize(DECIMAL_QUANTIZER, rounding=ROUND_HALF_UP),
            card=agg.card_total.quantize(DECIMAL_QUANTIZER, rounding=ROUND_HALF_UP),
            transfer=agg.transfer_total.quantize(DECIMAL_QUANTIZER, rounding=ROUND_HALF_UP),
        )

        return DailyReportResponse(
            date=agg.report_date,
            timezone=agg.timezone,
            total_sales=total_sales,
            transactions_count=agg.transactions_count,
            total_cost=total_cost,
            gross_margin=gross_margin,
            margin_percentage=margin_percentage,
            payment_breakdown=payment_breakdown,
        )
