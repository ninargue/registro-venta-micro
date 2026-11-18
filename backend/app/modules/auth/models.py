import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Business(Base):
    """Comercio / Tenant principal."""

    __tablename__ = "businesses"
    __table_args__ = (
        CheckConstraint("char_length(trim(name)) > 0", name="chk_businesses_name_not_empty"),
        CheckConstraint("char_length(country) = 2", name="chk_businesses_country_length"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    country: Mapped[str] = mapped_column(String(2), nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    users: Mapped[list[BusinessUser]] = relationship(
        "BusinessUser", back_populates="business", cascade="all, delete-orphan"
    )


class BusinessUser(Base):
    """Membresía y rol de un usuario en un comercio."""

    __tablename__ = "business_users"
    __table_args__ = (
        CheckConstraint("role IN ('owner', 'cashier')", name="chk_business_users_role_valid"),
        UniqueConstraint("user_id", name="uq_business_users_user_id"),
    )

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    business: Mapped[Business] = relationship("Business", back_populates="users")
