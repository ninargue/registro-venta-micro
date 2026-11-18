import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
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


class Product(Base):
    """Producto del catálogo e inventario por comercio."""

    __tablename__ = "products"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_products"),
        UniqueConstraint("business_id", "id", name="uq_products_business_id_id"),
        CheckConstraint(
            "code IS NULL OR char_length(trim(code)) > 0",
            name="chk_products_code_not_empty",
        ),
        CheckConstraint(
            "char_length(trim(name)) > 0",
            name="chk_products_name_not_empty",
        ),
        CheckConstraint("sale_price > 0", name="chk_products_sale_price_positive"),
        CheckConstraint("cost_price >= 0", name="chk_products_cost_price_non_negative"),
        Index(
            "uq_products_business_id_code",
            "business_id",
            "code",
            unique=True,
            postgresql_where=text("code IS NOT NULL"),
        ),
        Index("ix_products_business_id_active_name", "business_id", "is_active", "name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("businesses.id", name="fk_products_business_id", ondelete="CASCADE"),
        nullable=False,
    )
    code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    sale_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    cost_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        server_default=text("0"),
        nullable=False,
    )
    stock: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        server_default=text("0"),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        server_default=text("true"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
