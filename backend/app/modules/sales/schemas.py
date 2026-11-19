import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, WithJsonSchema, field_validator

from app.core.schemas import (
    MAX_NUMERIC_12_2,
    parse_strict_decimal,
    quantize_decimal,
    reject_nul_byte,
)

PaymentMethod = Literal["cash", "card", "transfer"]

DecimalInput = Annotated[
    Decimal,
    WithJsonSchema(
        {
            "type": "string",
            "format": "decimal",
            "pattern": r"^\d{1,10}(\.\d{1,2})?$",
        }
    ),
]


class SaleItemCreate(BaseModel):
    """Línea de producto en una solicitud de venta."""

    product_id: uuid.UUID = Field(description="Identificador del producto")
    quantity: DecimalInput = Field(
        gt=Decimal("0"),
        le=MAX_NUMERIC_12_2,
        max_digits=12,
        decimal_places=2,
        description="Cantidad vendida (string decimal exacto, sin float)",
        examples=["2.00"],
    )

    @field_validator("product_id", mode="before")
    @classmethod
    def validate_product_id_nul(cls, value: Any) -> Any:
        if isinstance(value, str):
            return reject_nul_byte(value)
        return value

    @field_validator("quantity", mode="before")
    @classmethod
    def validate_quantity(cls, value: Any) -> Decimal:
        return parse_strict_decimal(value)


class SalePaymentCreate(BaseModel):
    """Medio de pago e importe imputado en una venta."""

    payment_method: PaymentMethod = Field(
        description="Medio de pago admitido en MVP",
        examples=["cash"],
    )
    amount: DecimalInput = Field(
        gt=Decimal("0"),
        le=MAX_NUMERIC_12_2,
        max_digits=12,
        decimal_places=2,
        description="Importe imputado a este medio de pago (string decimal exacto)",
        examples=["3000.00"],
    )

    @field_validator("payment_method", mode="before")
    @classmethod
    def validate_payment_method_nul(cls, value: Any) -> Any:
        if isinstance(value, str):
            return reject_nul_byte(value)
        return value

    @field_validator("amount", mode="before")
    @classmethod
    def validate_amount(cls, value: Any) -> Decimal:
        return parse_strict_decimal(value)


class SaleCreate(BaseModel):
    """Payload de entrada para registrar una venta en POST /api/v1/sales."""

    model_config = ConfigDict(extra="ignore")

    client_id: uuid.UUID = Field(
        description="Identificador UUID v4 generado en cliente para idempotencia",
    )
    items: list[SaleItemCreate] = Field(
        min_length=1,
        max_length=500,
        description="Líneas de la venta",
    )
    payments: list[SalePaymentCreate] = Field(
        min_length=1,
        max_length=20,
        description="Desglose de pagos",
    )

    @field_validator("client_id", mode="before")
    @classmethod
    def validate_client_id_nul(cls, value: Any) -> Any:
        if isinstance(value, str):
            return reject_nul_byte(value)
        return value


class SaleItemResponse(BaseModel):
    """Línea de comprobante de venta (omite unit_cost intencionalmente)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    product_name: str
    quantity: Decimal
    unit_price: Decimal
    subtotal: Decimal

    @field_validator("quantity", "unit_price", "subtotal", mode="after")
    @classmethod
    def quantize_decimals(cls, value: Decimal) -> Decimal:
        return quantize_decimal(value)


class SalePaymentResponse(BaseModel):
    """Pago registrado en el comprobante de venta."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    payment_method: PaymentMethod
    amount: Decimal

    @field_validator("amount", mode="after")
    @classmethod
    def quantize_amount(cls, value: Decimal) -> Decimal:
        return quantize_decimal(value)


class SaleResponse(BaseModel):
    """Comprobante de venta persistido."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    total_amount: Decimal
    items: list[SaleItemResponse]
    payments: list[SalePaymentResponse]
    created_at: datetime

    @field_validator("total_amount", mode="after")
    @classmethod
    def quantize_total(cls, value: Decimal) -> Decimal:
        return quantize_decimal(value)
