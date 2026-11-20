"""harden rls policies, revoke grants, provision app_runtime role, and add updated_at trigger

Revision ID: f8b2c1a94d07
Revises: e4a7c2b91f03
Create Date: 2026-11-18 12:36:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f8b2c1a94d07"
down_revision: str | Sequence[str] | None = "e4a7c2b91f03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Restringir businesses_onboarding_insert a contexto válido de usuario y negocio
    op.execute("DROP POLICY IF EXISTS businesses_onboarding_insert ON businesses;")
    op.execute(
        """
        CREATE POLICY businesses_onboarding_insert ON businesses
        FOR INSERT
        WITH CHECK (
            NULLIF(current_setting('app.current_user_id', true), '')::uuid IS NOT NULL
            AND id = NULLIF(current_setting('app.current_business_id', true), '')::uuid
        );
        """
    )

    # 2. Revocar permisos heredados de PUBLIC, anon y authenticated
    op.execute("REVOKE ALL ON TABLE businesses, business_users FROM PUBLIC, anon, authenticated;")

    # 3. Endurecer políticas RLS en business_users (exigir current_business_id y distinción de role)
    op.execute("DROP POLICY IF EXISTS business_users_insert_own_user ON business_users;")
    op.execute(
        """
        CREATE POLICY business_users_insert_own_user ON business_users
        FOR INSERT
        WITH CHECK (
            user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
            AND business_id = NULLIF(current_setting('app.current_business_id', true), '')::uuid
        );
        """
    )

    op.execute("DROP POLICY IF EXISTS business_users_update_isolation ON business_users;")
    op.execute(
        """
        CREATE POLICY business_users_update_isolation ON business_users
        FOR UPDATE
        USING (
            business_id = NULLIF(current_setting('app.current_business_id', true), '')::uuid
            AND (
                NULLIF(current_setting('app.current_user_role', true), '') IS NULL
                OR current_setting('app.current_user_role', true) = 'owner'
            )
        )
        WITH CHECK (
            business_id = NULLIF(current_setting('app.current_business_id', true), '')::uuid
            AND (
                NULLIF(current_setting('app.current_user_role', true), '') IS NULL
                OR current_setting('app.current_user_role', true) = 'owner'
            )
        );
        """
    )

    op.execute("DROP POLICY IF EXISTS business_users_delete_isolation ON business_users;")
    op.execute(
        """
        CREATE POLICY business_users_delete_isolation ON business_users
        FOR DELETE
        USING (
            business_id = NULLIF(current_setting('app.current_business_id', true), '')::uuid
            AND (
                NULLIF(current_setting('app.current_user_role', true), '') IS NULL
                OR current_setting('app.current_user_role', true) = 'owner'
            )
        );
        """
    )

    # 4. Provisionar rol runtime dedicado con LOGIN y NOBYPASSRLS miembro de app_api
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_runtime') THEN
                CREATE ROLE app_runtime LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE
                    NOBYPASSRLS PASSWORD 'app_runtime_dev_password';
            END IF;
            IF NOT pg_has_role('app_runtime', 'app_api', 'MEMBER') THEN
                GRANT app_api TO app_runtime;
            END IF;
            IF NOT pg_has_role(current_user, 'app_runtime', 'SET') THEN
                EXECUTE format('GRANT app_runtime TO %I', current_user);
            END IF;
        END
        $$;
        """
    )

    # 5. Trigger automático para updated_at en businesses
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.set_businesses_updated_at()
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
        CREATE TRIGGER trg_businesses_set_updated_at
        BEFORE UPDATE ON businesses
        FOR EACH ROW
        EXECUTE FUNCTION public.set_businesses_updated_at();
        """
    )


def downgrade() -> None:
    # 1. Eliminar trigger y función updated_at
    op.execute("DROP TRIGGER IF EXISTS trg_businesses_set_updated_at ON businesses;")
    op.execute("DROP FUNCTION IF EXISTS public.set_businesses_updated_at();")

    # 2. Revocar y eliminar rol app_runtime
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_runtime') THEN
                IF pg_has_role(current_user, 'app_runtime', 'MEMBER') THEN
                    EXECUTE format('REVOKE app_runtime FROM %I', current_user);
                END IF;
                IF pg_has_role('app_runtime', 'app_api', 'MEMBER') THEN
                    REVOKE app_api FROM app_runtime;
                END IF;
                DROP ROLE app_runtime;
            END IF;
        END
        $$;
        """
    )

    # 3. Restaurar políticas previas en business_users
    op.execute("DROP POLICY IF EXISTS business_users_delete_isolation ON business_users;")
    op.execute(
        """
        CREATE POLICY business_users_delete_isolation ON business_users
        FOR DELETE
        USING (business_id = NULLIF(current_setting('app.current_business_id', true), '')::uuid);
        """
    )

    op.execute("DROP POLICY IF EXISTS business_users_update_isolation ON business_users;")
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

    op.execute("DROP POLICY IF EXISTS business_users_insert_own_user ON business_users;")
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

    # 4. Restaurar permisos previos de authenticated y businesses_onboarding_insert
    op.execute("GRANT ALL ON TABLE businesses TO authenticated;")
    op.execute("GRANT ALL ON TABLE business_users TO authenticated;")

    op.execute("DROP POLICY IF EXISTS businesses_onboarding_insert ON businesses;")
    op.execute(
        """
        CREATE POLICY businesses_onboarding_insert ON businesses
        FOR INSERT
        WITH CHECK (true);
        """
    )
