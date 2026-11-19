"""create sales, sale_items, and payments tables with indexes

Revision ID: d4e7f1a2b9c3
Revises: a3f9d2e1b4c8
Create Date: 2026-11-19 01:10:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "d4e7f1a2b9c3"
down_revision: str | Sequence[str] | None = "a3f9d2e1b4c8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Crear tabla padre sales
    op.create_table(
        "sales",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("total_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("total_amount > 0", name="chk_sales_total_amount_positive"),
        sa.ForeignKeyConstraint(
            ["business_id"],
            ["businesses.id"],
            name="fk_sales_business_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_sales"),
        sa.UniqueConstraint("business_id", "id", name="uq_sales_business_id_id"),
        sa.UniqueConstraint("business_id", "client_id", name="uq_sales_business_id_client_id"),
    )

    # 2. Crear tabla hijo sale_items
    op.create_table(
        "sale_items",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sale_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("unit_cost", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("quantity > 0", name="chk_sale_items_quantity_positive"),
        sa.CheckConstraint("unit_price > 0", name="chk_sale_items_unit_price_positive"),
        sa.CheckConstraint("unit_cost >= 0", name="chk_sale_items_unit_cost_non_negative"),
        sa.ForeignKeyConstraint(
            ["business_id"],
            ["businesses.id"],
            name="fk_sale_items_business_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["business_id", "sale_id"],
            ["sales.business_id", "sales.id"],
            name="fk_sale_items_sale",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["business_id", "product_id"],
            ["products.business_id", "products.id"],
            name="fk_sale_items_product",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_sale_items"),
    )

    # 3. Crear tabla hijo payments
    op.create_table(
        "payments",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sale_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payment_method", sa.String(length=20), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "payment_method IN ('cash', 'card', 'transfer')",
            name="chk_payments_method_valid",
        ),
        sa.CheckConstraint("amount > 0", name="chk_payments_amount_positive"),
        sa.ForeignKeyConstraint(
            ["business_id"],
            ["businesses.id"],
            name="fk_payments_business_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["business_id", "sale_id"],
            ["sales.business_id", "sales.id"],
            name="fk_payments_sale",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_payments"),
    )

    # 4. Crear índices B-tree liderados por business_id
    op.create_index(
        "ix_sales_business_id_created_at",
        "sales",
        ["business_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_sale_items_business_id_sale_id",
        "sale_items",
        ["business_id", "sale_id"],
        unique=False,
    )
    op.create_index(
        "ix_sale_items_business_id_product_id",
        "sale_items",
        ["business_id", "product_id"],
        unique=False,
    )
    op.create_index(
        "ix_payments_business_id_sale_id",
        "payments",
        ["business_id", "sale_id"],
        unique=False,
    )

    # 5. Habilitar y forzar RLS, políticas granulares y DCL de mínimo privilegio
    for table in ("sales", "sale_items", "payments"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;")

        op.execute(
            f"""
            CREATE POLICY {table}_select_isolation ON {table}
            FOR SELECT
            USING (
                business_id = NULLIF(current_setting('app.current_business_id', true), '')::uuid
            );
            """
        )
        op.execute(
            f"""
            CREATE POLICY {table}_insert_isolation ON {table}
            FOR INSERT
            WITH CHECK (
                business_id = NULLIF(current_setting('app.current_business_id', true), '')::uuid
            );
            """
        )
        op.execute(
            f"""
            CREATE POLICY {table}_update_isolation ON {table}
            FOR UPDATE
            USING (
                business_id = NULLIF(current_setting('app.current_business_id', true), '')::uuid
            )
            WITH CHECK (
                business_id = NULLIF(current_setting('app.current_business_id', true), '')::uuid
            );
            """
        )
        op.execute(
            f"""
            CREATE POLICY {table}_delete_isolation ON {table}
            FOR DELETE
            USING (
                business_id = NULLIF(current_setting('app.current_business_id', true), '')::uuid
            );
            """
        )

        op.execute(f"REVOKE ALL ON TABLE {table} FROM PUBLIC, anon, authenticated;")
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE {table} TO app_api;")


def downgrade() -> None:
    # 1. Revocar privilegios de app_api, eliminar políticas RLS y deshabilitar RLS en orden inverso
    for table in ("payments", "sale_items", "sales"):
        op.execute(f"REVOKE ALL ON TABLE {table} FROM app_api;")
        op.execute(f"DROP POLICY IF EXISTS {table}_delete_isolation ON {table};")
        op.execute(f"DROP POLICY IF EXISTS {table}_update_isolation ON {table};")
        op.execute(f"DROP POLICY IF EXISTS {table}_insert_isolation ON {table};")
        op.execute(f"DROP POLICY IF EXISTS {table}_select_isolation ON {table};")
        op.execute(f"ALTER TABLE IF EXISTS {table} NO FORCE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE IF EXISTS {table} DISABLE ROW LEVEL SECURITY;")

    # 2. Eliminar índices y tablas en orden inverso (payments -> sale_items -> sales)
    op.drop_index("ix_payments_business_id_sale_id", table_name="payments")
    op.drop_index("ix_sale_items_business_id_product_id", table_name="sale_items")
    op.drop_index("ix_sale_items_business_id_sale_id", table_name="sale_items")
    op.drop_index("ix_sales_business_id_created_at", table_name="sales")

    op.drop_table("payments")
    op.drop_table("sale_items")
    op.drop_table("sales")
