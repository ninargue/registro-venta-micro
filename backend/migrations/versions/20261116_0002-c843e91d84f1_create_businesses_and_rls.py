"""create businesses and business_users tables with rls

Revision ID: c843e91d84f1
Revises: ba617f3a8caa
Create Date: 2026-11-16 22:50:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "c843e91d84f1"
down_revision: str | Sequence[str] | None = "ba617f3a8caa"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Crear tabla businesses
    op.create_table(
        "businesses",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("country", sa.String(length=2), nullable=False),
        sa.Column("timezone", sa.String(length=50), nullable=False),
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
            "char_length(trim(name)) > 0",
            name="chk_businesses_name_not_empty",
        ),
        sa.CheckConstraint(
            "char_length(country) = 2",
            name="chk_businesses_country_length",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_businesses"),
    )

    # 2. Crear tabla business_users
    op.create_table(
        "business_users",
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "role IN ('owner', 'cashier')",
            name="chk_business_users_role_valid",
        ),
        sa.ForeignKeyConstraint(
            ["business_id"],
            ["businesses.id"],
            name="fk_business_users_business_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("business_id", "user_id", name="pk_business_users"),
    )

    # 3. Índice en user_id para búsquedas de comercios por usuario
    op.create_index(
        "ix_business_users_user_id",
        "business_users",
        ["user_id"],
        unique=False,
    )

    # 4. Habilitar y forzar Row-Level Security
    op.execute("ALTER TABLE businesses ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE businesses FORCE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE business_users ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE business_users FORCE ROW LEVEL SECURITY;")

    # 5. Políticas RLS de aislamiento multi-tenant
    op.execute(
        """
        CREATE POLICY businesses_tenant_isolation ON businesses
        FOR ALL
        USING (id = NULLIF(current_setting('app.current_business_id', true), '')::uuid);
        """
    )
    op.execute(
        """
        CREATE POLICY businesses_onboarding_insert ON businesses
        FOR INSERT
        WITH CHECK (true);
        """
    )

    op.execute(
        """
        CREATE POLICY business_users_tenant_isolation ON business_users
        FOR ALL
        USING (business_id = NULLIF(current_setting('app.current_business_id', true), '')::uuid);
        """
    )
    op.execute(
        """
        CREATE POLICY business_users_onboarding_insert ON business_users
        FOR INSERT
        WITH CHECK (true);
        """
    )

    # 6. Permisos DCL para roles de aplicación Supabase
    op.execute("GRANT ALL ON TABLE businesses TO authenticated, service_role;")
    op.execute("GRANT ALL ON TABLE business_users TO authenticated, service_role;")


def downgrade() -> None:
    # 1. Revocar permisos
    op.execute("REVOKE ALL ON TABLE business_users FROM authenticated, service_role;")
    op.execute("REVOKE ALL ON TABLE businesses FROM authenticated, service_role;")

    # 2. Eliminar políticas RLS
    op.execute("DROP POLICY IF EXISTS businesses_tenant_isolation ON businesses;")
    op.execute("DROP POLICY IF EXISTS businesses_onboarding_insert ON businesses;")
    op.execute("DROP POLICY IF EXISTS business_users_tenant_isolation ON business_users;")
    op.execute("DROP POLICY IF EXISTS business_users_onboarding_insert ON business_users;")

    # 3. Deshabilitar RLS
    op.execute("ALTER TABLE IF EXISTS business_users NO FORCE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE IF EXISTS business_users DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE IF EXISTS businesses NO FORCE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE IF EXISTS businesses DISABLE ROW LEVEL SECURITY;")

    # 4. Eliminar tablas
    op.drop_index("ix_business_users_user_id", table_name="business_users")
    op.drop_table("business_users")
    op.drop_table("businesses")
