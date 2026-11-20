import datetime as dt
import re
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.core.schemas import reject_nul_byte

DECIMAL_QUANTIZER = Decimal("0.01")
PERCENT_MULTIPLIER = Decimal("100")
MIN_REPORT_DATE = dt.date(1970, 1, 1)
MAX_REPORT_DATE = dt.date(2100, 12, 31)
_ISO_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class DailyReportQuery(BaseModel):
    """Parámetros de consulta para GET /api/v1/reports/daily."""

    date: dt.date | None = Field(
        default=None,
        description=(
            "Fecha local del reporte en formato ISO YYYY-MM-DD "
            "(por defecto, fecha actual en la zona horaria del comercio)"
        ),
        examples=["2026-11-19"],
    )

    @field_validator("date", mode="before")
    @classmethod
    def validate_date(cls, value: Any) -> dt.date | None:
        """Valida estrictamente fecha ISO YYYY-MM-DD dentro del rango operativo."""
        if value is None:
            return None

        if isinstance(value, bool | int | float | dt.datetime):
            raise ValueError("Date must be an ISO YYYY-MM-DD string or date")

        if isinstance(value, str):
            reject_nul_byte(value)
            cleaned = value.strip()
            if not _ISO_DATE_PATTERN.match(cleaned):
                raise ValueError("Date must follow ISO YYYY-MM-DD format")
            try:
                parsed = dt.date.fromisoformat(cleaned)
            except ValueError as exc:
                raise ValueError("Invalid calendar date") from exc
        elif isinstance(value, dt.date):
            parsed = value
        else:
            raise ValueError("Date must be an ISO YYYY-MM-DD string or date")

        if parsed < MIN_REPORT_DATE or parsed > MAX_REPORT_DATE:
            raise ValueError(
                f"Date must be between {MIN_REPORT_DATE.isoformat()} "
                f"and {MAX_REPORT_DATE.isoformat()}"
            )

        return parsed


class PaymentMethodBreakdown(BaseModel):
    """Desglose de recaudación diaria por medio de pago."""

    cash: Decimal = Field(
        description="Total recaudado en efectivo",
        examples=["15000.00"],
    )
    card: Decimal = Field(
        description="Total recaudado con tarjeta",
        examples=["10000.00"],
    )
    transfer: Decimal = Field(
        description="Total recaudado por transferencia/QR",
        examples=["5000.00"],
    )

    @field_validator("cash", "card", "transfer", mode="after")
    @classmethod
    def quantize_amount(cls, value: Decimal) -> Decimal:
        """Cuantiza montos monetarios a 2 decimales con ROUND_HALF_UP."""
        return value.quantize(DECIMAL_QUANTIZER, rounding=ROUND_HALF_UP)


class DailyReportResponse(BaseModel):
    """Consolidado diario de ventas, medios de pago, costos y margen bruto."""

    date: dt.date = Field(
        description="Fecha local consolidada en la zona horaria del comercio",
        examples=["2026-11-19"],
    )
    timezone: str = Field(
        description="Zona horaria IANA aplicada al corte diario",
        examples=["America/Argentina/Buenos_Aires"],
    )
    total_sales: Decimal = Field(
        description="Total bruto facturado en el día",
        examples=["30000.00"],
    )
    transactions_count: int = Field(
        ge=0,
        description="Cantidad total de ventas registradas en el día",
        examples=[3],
    )
    total_cost: Decimal = Field(
        description="Costo total acumulado de mercadería vendida (SUM(quantity * unit_cost))",
        examples=["21000.00"],
    )
    gross_margin: Decimal = Field(
        description="Margen bruto estimado (total_sales - total_cost)",
        examples=["9000.00"],
    )
    margin_percentage: Decimal = Field(
        description=(
            "Porcentaje de rentabilidad sobre ventas ((gross_margin / total_sales) * 100); "
            "0.00 si no hay ventas"
        ),
        examples=["30.00"],
    )
    payment_breakdown: PaymentMethodBreakdown = Field(
        description="Desglose de recaudación por medio de pago",
    )

    @field_validator(
        "total_sales",
        "total_cost",
        "gross_margin",
        "margin_percentage",
        mode="after",
    )
    @classmethod
    def quantize_metrics(cls, value: Decimal) -> Decimal:
        """Cuantiza métricas monetarias y porcentuales a 2 decimales con ROUND_HALF_UP."""
        return value.quantize(DECIMAL_QUANTIZER, rounding=ROUND_HALF_UP)
