import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Numeric,
    PrimaryKeyConstraint,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Sale(Base):
    """Cabecera de venta por comercio con llave de idempotencia."""

    __tablename__ = "sales"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_sales"),
        UniqueConstraint("business_id", "id", name="uq_sales_business_id_id"),
        UniqueConstraint("business_id", "client_id", name="uq_sales_business_id_client_id"),
        CheckConstraint("total_amount > 0", name="chk_sales_total_amount_positive"),
        Index("ix_sales_business_id_created_at", "business_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("businesses.id", name="fk_sales_business_id", ondelete="CASCADE"),
        nullable=False,
    )
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class SaleItem(Base):
    """Línea de venta con snapshot congelado de precio y costo unitario."""

    __tablename__ = "sale_items"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_sale_items"),
        ForeignKeyConstraint(
            ["business_id", "sale_id"],
            ["sales.business_id", "sales.id"],
            name="fk_sale_items_sale",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["business_id", "product_id"],
            ["products.business_id", "products.id"],
            name="fk_sale_items_product",
            ondelete="RESTRICT",
        ),
        CheckConstraint("quantity > 0", name="chk_sale_items_quantity_positive"),
        CheckConstraint("unit_price > 0", name="chk_sale_items_unit_price_positive"),
        CheckConstraint("unit_cost >= 0", name="chk_sale_items_unit_cost_non_negative"),
        Index("ix_sale_items_business_id_sale_id", "business_id", "sale_id"),
        Index("ix_sale_items_business_id_product_id", "business_id", "product_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("businesses.id", name="fk_sale_items_business_id", ondelete="CASCADE"),
        nullable=False,
    )
    sale_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class Payment(Base):
    """Registro de pago asociado a una venta."""

    __tablename__ = "payments"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_payments"),
        ForeignKeyConstraint(
            ["business_id", "sale_id"],
            ["sales.business_id", "sales.id"],
            name="fk_payments_sale",
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "payment_method IN ('cash', 'card', 'transfer')",
            name="chk_payments_method_valid",
        ),
        CheckConstraint("amount > 0", name="chk_payments_amount_positive"),
        Index("ix_payments_business_id_sale_id", "business_id", "sale_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("businesses.id", name="fk_payments_business_id", ondelete="CASCADE"),
        nullable=False,
    )
    sale_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    payment_method: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
