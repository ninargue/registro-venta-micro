import uuid
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.schemas import reject_nul_byte

MAX_NUMERIC_12_2 = Decimal("9999999999.99")
DECIMAL_QUANTIZER = Decimal("0.01")
UPDATABLE_PRODUCT_FIELDS: frozenset[str] = frozenset(
    {"code", "name", "sale_price", "cost_price", "stock"}
)
_NON_NULLABLE_UPDATE_FIELDS: tuple[str, ...] = ("name", "sale_price", "cost_price", "stock")


def _validate_optional_code(value: Any) -> str | None:
    """Valida y normaliza el código/SKU opcional del producto."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("Product code must be a string")
    reject_nul_byte(value)
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("Product code cannot be empty")
    return cleaned


def _validate_product_name(value: Any) -> str:
    """Valida y normaliza el nombre obligatorio del producto."""
    if not isinstance(value, str):
        raise ValueError("Product name must be a string")
    reject_nul_byte(value)
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("Product name cannot be empty")
    return cleaned


def _parse_strict_decimal(value: Any) -> Decimal:
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


class ProductCreate(BaseModel):
    """Payload de entrada para crear un producto en POST /api/v1/catalog/products."""

    code: str | None = Field(
        default=None,
        max_length=50,
        description="Código interno o SKU opcional",
        examples=["SKU-001"],
    )
    name: str = Field(
        min_length=1,
        max_length=150,
        description="Nombre del producto",
        examples=["Yerba Mate 1kg"],
    )
    sale_price: Decimal = Field(
        gt=Decimal("0"),
        le=MAX_NUMERIC_12_2,
        max_digits=12,
        decimal_places=2,
        description="Precio de venta bruto (sin impuestos)",
        examples=["3500.50"],
    )
    cost_price: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0"),
        le=MAX_NUMERIC_12_2,
        max_digits=12,
        decimal_places=2,
        description="Costo unitario de referencia",
        examples=["2200.00"],
    )
    stock: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0"),
        le=MAX_NUMERIC_12_2,
        max_digits=12,
        decimal_places=2,
        description="Stock inicial del producto",
        examples=["10.00"],
    )

    @field_validator("code", mode="before")
    @classmethod
    def validate_code(cls, value: Any) -> str | None:
        return _validate_optional_code(value)

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, value: Any) -> str:
        return _validate_product_name(value)

    @field_validator("sale_price", "cost_price", "stock", mode="before")
    @classmethod
    def validate_decimals(cls, value: Any) -> Decimal:
        return _parse_strict_decimal(value)


class ProductUpdate(BaseModel):
    """Payload de entrada para actualizar parcialmente un producto en PATCH."""

    code: str | None = Field(
        default=None,
        max_length=50,
        description="Código interno o SKU opcional",
        examples=["SKU-001"],
    )
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=150,
        description="Nombre del producto",
        examples=["Yerba Mate 1kg"],
    )
    sale_price: Decimal | None = Field(
        default=None,
        gt=Decimal("0"),
        le=MAX_NUMERIC_12_2,
        max_digits=12,
        decimal_places=2,
        description="Precio de venta bruto (sin impuestos)",
        examples=["3500.50"],
    )
    cost_price: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        le=MAX_NUMERIC_12_2,
        max_digits=12,
        decimal_places=2,
        description="Costo unitario de referencia",
        examples=["2200.00"],
    )
    stock: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        le=MAX_NUMERIC_12_2,
        max_digits=12,
        decimal_places=2,
        description="Stock actual del producto",
        examples=["10.00"],
    )

    @field_validator("code", mode="before")
    @classmethod
    def validate_code(cls, value: Any) -> str | None:
        return _validate_optional_code(value)

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, value: Any) -> str:
        return _validate_product_name(value)

    @field_validator("sale_price", "cost_price", "stock", mode="before")
    @classmethod
    def validate_decimals(cls, value: Any) -> Decimal:
        return _parse_strict_decimal(value)

    @model_validator(mode="after")
    def validate_non_empty_and_non_nullable_fields(self) -> Self:
        editable_set = self.model_fields_set & UPDATABLE_PRODUCT_FIELDS
        if not editable_set:
            raise ValueError("At least one editable field must be provided")
        for field_name in _NON_NULLABLE_UPDATE_FIELDS:
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"Field '{field_name}' cannot be null")
        return self


class ProductListQuery(BaseModel):
    """Parámetros de consulta validados para GET /api/v1/catalog/products."""

    q: str | None = Field(
        default=None,
        max_length=150,
        description="Búsqueda parcial por nombre o código",
    )
    include_inactive: bool = Field(
        default=False,
        description="Incluir productos desactivados",
    )
    limit: int = Field(
        default=50,
        ge=1,
        le=200,
        description="Cantidad máxima de resultados por página",
    )
    offset: int = Field(
        default=0,
        ge=0,
        le=2_147_483_647,
        description="Desplazamiento para paginación",
    )

    @field_validator("q", mode="before")
    @classmethod
    def validate_query(cls, value: Any) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("Search query must be a string")
        reject_nul_byte(value)
        cleaned = value.strip()
        return cleaned or None


class ProductResponse(BaseModel):
    """Representación de salida de un producto del catálogo."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str | None
    name: str
    sale_price: Decimal
    cost_price: Decimal | None
    stock: Decimal
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @field_validator("sale_price", "cost_price", "stock", mode="after")
    @classmethod
    def quantize_decimals(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return None
        return value.quantize(DECIMAL_QUANTIZER)


class ProductListResponse(BaseModel):
    """Respuesta paginada de productos del catálogo."""

    items: list[ProductResponse]
    total: int
    limit: int
    offset: int
