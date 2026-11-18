"""fix businesses rls policies, app_api grants, and unique user_id on business_users

Revision ID: e4a7c2b91f03
Revises: c843e91d84f1
Create Date: 2026-11-17 23:35:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e4a7c2b91f03"
down_revision: str | Sequence[str] | None = "c843e91d84f1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Reemplazar índice no único ix_business_users_user_id por restricción UNIQUE (user_id)
    op.drop_index("ix_business_users_user_id", table_name="business_users")
    op.create_unique_constraint(
        "uq_business_users_user_id",
        "business_users",
        ["user_id"],
    )

    # 2. [db-security-agent] Políticas RLS granulares en business_users (Tarea 3.1)
    op.execute("DROP POLICY IF EXISTS business_users_tenant_isolation ON business_users;")
    op.execute("DROP POLICY IF EXISTS business_users_onboarding_insert ON business_users;")

    op.execute(
        """
        CREATE POLICY business_users_select_isolation ON business_users
        FOR SELECT
        USING (
            business_id = NULLIF(current_setting('app.current_business_id', true), '')::uuid
            OR user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
        );
        """
    )
    op.execute(
        """
        CREATE POLICY business_users_insert_own_user ON business_users
        FOR INSERT
        WITH CHECK (
            user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
            AND (
                NULLIF(current_setting('app.current_business_id', true), '')::uuid IS NULL
                OR business_id = NULLIF(current_setting('app.current_business_id', true), '')::uuid
            )
        );
        """
    )
    op.execute(
        """
        CREATE POLICY business_users_update_isolation ON business_users
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
        CREATE POLICY business_users_delete_isolation ON business_users
        FOR DELETE
        USING (business_id = NULLIF(current_setting('app.current_business_id', true), '')::uuid);
        """
    )

    # 3. [db-security-agent] Provisión idempotente de rol app_api y permisos DCL (Tarea 3.2)
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_api') THEN
                CREATE ROLE app_api NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
            END IF;
            IF NOT pg_has_role(current_user, 'app_api', 'SET') THEN
                EXECUTE format('GRANT app_api TO %I', current_user);
            END IF;
        END
        $$;
        """
    )
    op.execute("GRANT USAGE ON SCHEMA public TO app_api;")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE businesses TO app_api;")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE business_users TO app_api;")


def downgrade() -> None:
    # 1. [db-security-agent] Revocar permisos DCL de app_api (Tarea 3.3)
    op.execute("REVOKE ALL ON TABLE business_users FROM app_api;")
    op.execute("REVOKE ALL ON TABLE businesses FROM app_api;")
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_api')
               AND pg_has_role(current_user, 'app_api', 'MEMBER') THEN
                EXECUTE format('REVOKE app_api FROM %I', current_user);
            END IF;
        END
        $$;
        """
    )

    # 2. [db-security-agent] Restaurar políticas RLS previas de c843e91d84f1 (Tarea 3.3)
    op.execute("DROP POLICY IF EXISTS business_users_delete_isolation ON business_users;")
    op.execute("DROP POLICY IF EXISTS business_users_update_isolation ON business_users;")
    op.execute("DROP POLICY IF EXISTS business_users_insert_own_user ON business_users;")
    op.execute("DROP POLICY IF EXISTS business_users_select_isolation ON business_users;")

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

    # 3. Revertir uq_business_users_user_id a índice no único ix_business_users_user_id
    op.drop_constraint(
        "uq_business_users_user_id",
        "business_users",
        type_="unique",
    )
    op.create_index(
        "ix_business_users_user_id",
        "business_users",
        ["user_id"],
        unique=False,
    )
