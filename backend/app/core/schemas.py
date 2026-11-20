from decimal import Decimal, InvalidOperation
from typing import Any

from pydantic import BaseModel

MAX_NUMERIC_12_2 = Decimal("9999999999.99")
DECIMAL_QUANTIZER = Decimal("0.01")


def reject_nul_byte(value: str) -> str:
    """Rechaza cadenas que contengan bytes NUL (\\x00)."""
    if "\x00" in value:
        raise ValueError("Input must not contain NUL bytes")
    return value


def parse_strict_decimal(value: Any) -> Decimal:
    """Valida Decimal estricto sin float/bool/NaN/Infinity ni redondeo silencioso (>2 decimales)."""
    if value is None or isinstance(value, bool | float):
        raise ValueError("Value must be an exact decimal string, integer, or Decimal")

    if isinstance(value, Decimal):
        parsed = value
    elif isinstance(value, int):
        parsed = Decimal(value)
    elif isinstance(value, str):
        reject_nul_byte(value)
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Decimal string cannot be empty")
        try:
            parsed = Decimal(cleaned)
        except InvalidOperation as exc:
            raise ValueError("Invalid decimal format") from exc
    else:
        raise ValueError("Value must be an exact decimal string, integer, or Decimal")

    if not parsed.is_finite():
        raise ValueError("Decimal value must be finite")

    exponent = parsed.as_tuple().exponent
    if isinstance(exponent, int) and exponent < -2:
        raise ValueError("At most 2 decimal places are allowed")

    if abs(parsed) > MAX_NUMERIC_12_2:
        raise ValueError("Decimal value exceeds numeric(12,2) range")

    try:
        return parsed.quantize(DECIMAL_QUANTIZER)
    except InvalidOperation as exc:
        raise ValueError("Decimal value exceeds supported precision") from exc


def quantize_decimal(value: Decimal) -> Decimal:
    """Cuantiza un Decimal a exactamente 2 decimales."""
    return value.quantize(DECIMAL_QUANTIZER)


class ErrorResponse(BaseModel):
    """Estructura estándar de error en respuestas HTTP de la API."""

    code: str
    message: str
    details: Any | None = None
