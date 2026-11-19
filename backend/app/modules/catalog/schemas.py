import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.schemas import (
    MAX_NUMERIC_12_2,
    parse_strict_decimal,
    quantize_decimal,
    reject_nul_byte,
)

_parse_strict_decimal = parse_strict_decimal


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
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("Product code must be a string")
        reject_nul_byte(value)
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Product code cannot be empty")
        return cleaned

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, value: Any) -> str:
        if not isinstance(value, str):
            raise ValueError("Product name must be a string")
        reject_nul_byte(value)
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Product name cannot be empty")
        return cleaned

    @field_validator("sale_price", "cost_price", "stock", mode="before")
    @classmethod
    def validate_decimals(cls, value: Any) -> Decimal:
        return _parse_strict_decimal(value)


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
        return quantize_decimal(value)


class ProductListResponse(BaseModel):
    """Respuesta paginada de productos del catálogo."""

    items: list[ProductResponse]
    total: int
    limit: int
    offset: int
