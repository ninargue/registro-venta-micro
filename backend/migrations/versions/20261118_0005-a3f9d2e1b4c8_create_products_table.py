"""create products table, indexes, and updated_at trigger

Revision ID: a3f9d2e1b4c8
Revises: f8b2c1a94d07
Create Date: 2026-11-18 20:52:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a3f9d2e1b4c8"
down_revision: str | Sequence[str] | None = "f8b2c1a94d07"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Crear tabla products
    op.create_table(
        "products",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=True),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("sale_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column(
            "cost_price",
            sa.Numeric(precision=12, scale=2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "stock",
            sa.Numeric(precision=12, scale=2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "code IS NULL OR char_length(trim(code)) > 0",
            name="chk_products_code_not_empty",
        ),
        sa.CheckConstraint(
            "char_length(trim(name)) > 0",
            name="chk_products_name_not_empty",
        ),
        sa.CheckConstraint("sale_price > 0", name="chk_products_sale_price_positive"),
        sa.CheckConstraint("cost_price >= 0", name="chk_products_cost_price_non_negative"),
        sa.ForeignKeyConstraint(
            ["business_id"],
            ["businesses.id"],
            name="fk_products_business_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_products"),
        sa.UniqueConstraint("business_id", "id", name="uq_products_business_id_id"),
    )

    # 2. Índices: unicidad parcial de code por negocio y listado activo ordenado por nombre
    op.create_index(
        "uq_products_business_id_code",
        "products",
        ["business_id", "code"],
        unique=True,
        postgresql_where=sa.text("code IS NOT NULL"),
    )
    op.create_index(
        "ix_products_business_id_active_name",
        "products",
        ["business_id", "is_active", "name"],
        unique=False,
    )

    # 3. Función y trigger BEFORE UPDATE para updated_at
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.set_products_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = clock_timestamp();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_products_set_updated_at
        BEFORE UPDATE ON products
        FOR EACH ROW
        EXECUTE FUNCTION public.set_products_updated_at();
        """
    )

    # 4. Habilitar y forzar Row-Level Security (RLS)
    op.execute("ALTER TABLE products ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE products FORCE ROW LEVEL SECURITY;")

    # 5. Políticas RLS granulares por operación aisladas por app.current_business_id
    op.execute(
        """
        CREATE POLICY products_select_isolation ON products
        FOR SELECT
        USING (
            business_id = NULLIF(current_setting('app.current_business_id', true), '')::uuid
        );
        """
    )
    op.execute(
        """
        CREATE POLICY products_insert_isolation ON products
        FOR INSERT
        WITH CHECK (
            business_id = NULLIF(current_setting('app.current_business_id', true), '')::uuid
        );
        """
    )
    op.execute(
        """
        CREATE POLICY products_update_isolation ON products
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
        """
        CREATE POLICY products_delete_isolation ON products
        FOR DELETE
        USING (
            business_id = NULLIF(current_setting('app.current_business_id', true), '')::uuid
        );
        """
    )

    # 6. DCL de mínimo privilegio (sin TRUNCATE, heredado por app_runtime vía app_api)
    op.execute("REVOKE ALL ON TABLE products FROM PUBLIC, anon, authenticated;")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE products TO app_api;")


def downgrade() -> None:
    # 1. Revocar privilegios de app_api, eliminar políticas RLS y deshabilitar/no forzar RLS
    op.execute("REVOKE ALL ON TABLE products FROM app_api;")
    op.execute("DROP POLICY IF EXISTS products_delete_isolation ON products;")
    op.execute("DROP POLICY IF EXISTS products_update_isolation ON products;")
    op.execute("DROP POLICY IF EXISTS products_insert_isolation ON products;")
    op.execute("DROP POLICY IF EXISTS products_select_isolation ON products;")
    op.execute("ALTER TABLE IF EXISTS products NO FORCE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE IF EXISTS products DISABLE ROW LEVEL SECURITY;")

    # 2. Eliminar trigger y función updated_at
    op.execute("DROP TRIGGER IF EXISTS trg_products_set_updated_at ON products;")
    op.execute("DROP FUNCTION IF EXISTS public.set_products_updated_at();")

    # 3. Eliminar índices y tabla products
    op.drop_index("ix_products_business_id_active_name", table_name="products")
    op.drop_index("uq_products_business_id_code", table_name="products")
    op.drop_table("products")
