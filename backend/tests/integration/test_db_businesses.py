import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.negocios


@pytest.mark.asyncio
async def test_insert_business_valid(db_session: AsyncSession) -> None:
    business_id = str(uuid.uuid4())
    async with db_session.begin() as tx:
        try:
            await db_session.execute(
                text(
                    """
                    INSERT INTO businesses (id, name, country, timezone)
                    VALUES (:id, :name, :country, :timezone)
                    """
                ),
                {
                    "id": business_id,
                    "name": "Kiosco San Martin",
                    "country": "AR",
                    "timezone": "America/Argentina/Buenos_Aires",
                },
            )
            result = await db_session.execute(
                text("SELECT id, name, country, timezone FROM businesses WHERE id = :id"),
                {"id": business_id},
            )
            row = result.mappings().one()
            assert str(row["id"]) == business_id
            assert row["name"] == "Kiosco San Martin"
            assert row["country"] == "AR"
            assert row["timezone"] == "America/Argentina/Buenos_Aires"
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_insert_business_rejects_nulls(db_session: AsyncSession) -> None:
    business_id = str(uuid.uuid4())
    with pytest.raises(IntegrityError) as exc_info:
        async with db_session.begin():
            await db_session.execute(
                text(
                    """
                    INSERT INTO businesses (id, name, country, timezone)
                    VALUES (:id, NULL, 'AR', 'America/Argentina/Buenos_Aires')
                    """
                ),
                {"id": business_id},
            )
    _assert_sqlstate(exc_info.value, "23502")


@pytest.mark.asyncio
async def test_insert_business_rejects_invalid_country_length(db_session: AsyncSession) -> None:
    business_id = str(uuid.uuid4())
    with pytest.raises(IntegrityError) as exc_country:
        async with db_session.begin():
            await db_session.execute(
                text(
                    """
                    INSERT INTO businesses (id, name, country, timezone)
                    VALUES (:id, 'Test Store', 'A', 'America/Argentina/Buenos_Aires')
                    """
                ),
                {"id": business_id},
            )
    _assert_sqlstate(exc_country.value, "23514")

    with pytest.raises(IntegrityError) as exc_name:
        async with db_session.begin():
            await db_session.execute(
                text(
                    """
                    INSERT INTO businesses (id, name, country, timezone)
                    VALUES (:id, '   ', 'AR', 'America/Argentina/Buenos_Aires')
                    """
                ),
                {"id": business_id},
            )
    _assert_sqlstate(exc_name.value, "23514")


@pytest.mark.asyncio
async def test_business_users_membership_and_valid_role(db_session: AsyncSession) -> None:
    business_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    async with db_session.begin() as tx:
        try:
            await db_session.execute(
                text(
                    """
                    INSERT INTO businesses (id, name, country, timezone)
                    VALUES (:id, :name, :country, :timezone)
                    """
                ),
                {
                    "id": business_id,
                    "name": "Ferreteria Central",
                    "country": "UY",
                    "timezone": "America/Montevideo",
                },
            )
            await db_session.execute(
                text(
                    """
                    INSERT INTO business_users (business_id, user_id, role)
                    VALUES (:b_id, :u_id, :role)
                    """
                ),
                {"b_id": business_id, "u_id": user_id, "role": "owner"},
            )
            res = await db_session.execute(
                text(
                    "SELECT role FROM business_users WHERE business_id = :b_id AND user_id = :u_id"
                ),
                {"b_id": business_id, "u_id": user_id},
            )
            assert res.scalar_one() == "owner"
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_business_users_rejects_invalid_role(db_session: AsyncSession) -> None:
    business_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    with pytest.raises(IntegrityError) as exc_info:
        async with db_session.begin():
            await db_session.execute(
                text(
                    """
                    INSERT INTO businesses (id, name, country, timezone)
                    VALUES (:id, 'Almacen', 'CL', 'America/Santiago')
                    """
                ),
                {"id": business_id},
            )
            await db_session.execute(
                text(
                    """
                    INSERT INTO business_users (business_id, user_id, role)
                    VALUES (:b_id, :u_id, 'superadmin')
                    """
                ),
                {"b_id": business_id, "u_id": user_id},
            )
    _assert_sqlstate(exc_info.value, "23514")


@pytest.mark.asyncio
async def test_business_users_rejects_orphan_business_id(db_session: AsyncSession) -> None:
    non_existent_business_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    with pytest.raises(IntegrityError) as exc_info:
        async with db_session.begin():
            await db_session.execute(
                text(
                    """
                    INSERT INTO business_users (business_id, user_id, role)
                    VALUES (:b_id, :u_id, 'owner')
                    """
                ),
                {"b_id": non_existent_business_id, "u_id": user_id},
            )
    _assert_sqlstate(exc_info.value, "23503")


@pytest.mark.asyncio
async def test_business_users_cascade_delete(db_session: AsyncSession) -> None:
    business_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    async with db_session.begin() as tx:
        try:
            await db_session.execute(
                text(
                    """
                    INSERT INTO businesses (id, name, country, timezone)
                    VALUES (:id, 'Panaderia', 'AR', 'America/Argentina/Buenos_Aires')
                    """
                ),
                {"id": business_id},
            )
            await db_session.execute(
                text(
                    """
                    INSERT INTO business_users (business_id, user_id, role)
                    VALUES (:b_id, :u_id, 'owner')
                    """
                ),
                {"b_id": business_id, "u_id": user_id},
            )
            await db_session.execute(
                text("DELETE FROM businesses WHERE id = :id"),
                {"id": business_id},
            )
            res = await db_session.execute(
                text("SELECT count(*) FROM business_users WHERE business_id = :b_id"),
                {"b_id": business_id},
            )
            assert res.scalar_one() == 0
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_rls_isolation_by_session_variable(db_session: AsyncSession) -> None:
    b1 = str(uuid.uuid4())
    b2 = str(uuid.uuid4())
    async with db_session.begin() as tx:
        try:
            await db_session.execute(
                text(
                    """
                    INSERT INTO businesses (id, name, country, timezone) VALUES
                    (:b1, 'Negocio 1', 'AR', 'America/Argentina/Buenos_Aires'),
                    (:b2, 'Negocio 2', 'AR', 'America/Argentina/Buenos_Aires')
                    """
                ),
                {"b1": b1, "b2": b2},
            )

            # Switch to non-superuser role so PostgreSQL enforces RLS
            await db_session.execute(text("SET LOCAL ROLE app_api;"))

            # Set tenant context to b1
            await db_session.execute(text(f"SET LOCAL app.current_business_id = '{b1}';"))
            result = await db_session.execute(text("SELECT id FROM businesses;"))
            ids = [str(r[0]) for r in result.fetchall()]
            assert b1 in ids
            assert b2 not in ids

            # No tenant context set -> should return empty under RLS
            await db_session.execute(text("SET LOCAL app.current_business_id = '';"))
            result_empty = await db_session.execute(text("SELECT id FROM businesses;"))
            assert len(result_empty.fetchall()) == 0
        finally:
            await tx.rollback()


async def _insert_business(
    db_session: AsyncSession, business_id: str, name: str = "Comercio"
) -> None:
    # Migration 0004 hardened businesses_onboarding_insert:
    # requires current_user_id + current_business_id.
    await db_session.execute(text(f"SET LOCAL app.current_user_id = '{uuid.uuid4()}';"))
    await db_session.execute(text(f"SET LOCAL app.current_business_id = '{business_id}';"))
    await db_session.execute(
        text(
            """
            INSERT INTO businesses (id, name, country, timezone)
            VALUES (:id, :name, 'AR', 'America/Argentina/Buenos_Aires')
            """
        ),
        {"id": business_id, "name": name},
    )


async def _insert_business_user(
    db_session: AsyncSession,
    business_id: str,
    user_id: str,
    role: str = "owner",
) -> None:
    # Migration 0004 hardened business_users_insert_own_user:
    # requires user_id + business_id GUCs.
    await db_session.execute(text(f"SET LOCAL app.current_user_id = '{user_id}';"))
    await db_session.execute(text(f"SET LOCAL app.current_business_id = '{business_id}';"))
    await db_session.execute(
        text(
            """
            INSERT INTO business_users (business_id, user_id, role)
            VALUES (:b_id, :u_id, :role)
            """
        ),
        {"b_id": business_id, "u_id": user_id, "role": role},
    )


def _assert_sqlstate(exc: DBAPIError, expected_sqlstate: str) -> None:
    orig = exc.orig
    sqlstate = getattr(orig, "sqlstate", None) or getattr(
        getattr(orig, "__cause__", None), "sqlstate", None
    )
    assert sqlstate == expected_sqlstate, (
        f"Expected SQLSTATE {expected_sqlstate}, got {sqlstate!r} ({exc})"
    )


@pytest.mark.asyncio
async def test_business_users_rejects_duplicate_user_id(db_session: AsyncSession) -> None:
    b1 = str(uuid.uuid4())
    b2 = str(uuid.uuid4())
    user_id = str(uuid.uuid4())

    async with db_session.begin() as tx:
        try:
            await _insert_business(db_session, b1, "Negocio A")
            await _insert_business(db_session, b2, "Negocio B")
            await _insert_business_user(db_session, b1, user_id, "owner")

            with pytest.raises(IntegrityError) as exc_info:
                async with db_session.begin_nested():
                    await _insert_business_user(db_session, b2, user_id, "owner")

            _assert_sqlstate(exc_info.value, "23505")
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_rls_business_users_select_by_business_id(db_session: AsyncSession) -> None:
    b1 = str(uuid.uuid4())
    b2 = str(uuid.uuid4())
    u1 = str(uuid.uuid4())
    u2 = str(uuid.uuid4())

    async with db_session.begin() as tx:
        try:
            await _insert_business(db_session, b1, "Negocio 1")
            await _insert_business(db_session, b2, "Negocio 2")
            await _insert_business_user(db_session, b1, u1, "owner")
            await _insert_business_user(db_session, b2, u2, "owner")

            await db_session.execute(text("SET LOCAL ROLE app_api;"))
            await db_session.execute(text(f"SET LOCAL app.current_business_id = '{b1}';"))

            rows = (
                await db_session.execute(text("SELECT business_id, user_id FROM business_users;"))
            ).fetchall()
            assert [(str(r[0]), str(r[1])) for r in rows] == [(b1, u1)]

            cross_rows = (
                await db_session.execute(
                    text("SELECT business_id FROM business_users WHERE business_id = :b2;"),
                    {"b2": b2},
                )
            ).fetchall()
            assert cross_rows == []

            await db_session.execute(text("SET LOCAL app.current_business_id = '';"))
            empty_rows = (
                await db_session.execute(text("SELECT business_id FROM business_users;"))
            ).fetchall()
            assert empty_rows == []
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_rls_business_users_login_select_by_current_user_id(
    db_session: AsyncSession,
) -> None:
    b1 = str(uuid.uuid4())
    b2 = str(uuid.uuid4())
    u_a = str(uuid.uuid4())
    u_b = str(uuid.uuid4())

    async with db_session.begin() as tx:
        try:
            await _insert_business(db_session, b1, "Negocio A")
            await _insert_business(db_session, b2, "Negocio B")
            await _insert_business_user(db_session, b1, u_a, "owner")
            await _insert_business_user(db_session, b2, u_b, "owner")

            await db_session.execute(text("SET LOCAL ROLE app_api;"))
            await db_session.execute(text(f"SET LOCAL app.current_user_id = '{u_a}';"))

            rows = (
                await db_session.execute(
                    text("SELECT business_id, user_id, role FROM business_users;")
                )
            ).fetchall()
            assert [(str(r[0]), str(r[1]), r[2]) for r in rows] == [(b1, u_a, "owner")]
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_rls_business_users_cross_user_select_blocked(db_session: AsyncSession) -> None:
    b1 = str(uuid.uuid4())
    b2 = str(uuid.uuid4())
    u_a = str(uuid.uuid4())
    u_b = str(uuid.uuid4())

    async with db_session.begin() as tx:
        try:
            await _insert_business(db_session, b1, "Negocio 1")
            await _insert_business(db_session, b2, "Negocio 2")
            await _insert_business_user(db_session, b1, u_a, "owner")
            await _insert_business_user(db_session, b2, u_b, "owner")

            await db_session.execute(text("SET LOCAL ROLE app_api;"))
            await db_session.execute(text(f"SET LOCAL app.current_user_id = '{u_a}';"))

            rows = (
                await db_session.execute(
                    text("SELECT business_id, user_id FROM business_users WHERE user_id = :u_b;"),
                    {"u_b": u_b},
                )
            ).fetchall()
            assert rows == []
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_rls_business_users_insert_own_user_allowed(db_session: AsyncSession) -> None:
    b1 = str(uuid.uuid4())
    u_a = str(uuid.uuid4())

    async with db_session.begin() as tx:
        try:
            await _insert_business(db_session, b1, "Onboarding Store")

            await db_session.execute(text("SET LOCAL ROLE app_api;"))
            await db_session.execute(text(f"SET LOCAL app.current_user_id = '{u_a}';"))
            await db_session.execute(text(f"SET LOCAL app.current_business_id = '{b1}';"))

            await _insert_business_user(db_session, b1, u_a, "owner")

            row = (
                await db_session.execute(
                    text(
                        "SELECT business_id, user_id, role FROM business_users WHERE user_id = :u;"
                    ),
                    {"u": u_a},
                )
            ).one()
            assert (str(row[0]), str(row[1]), row[2]) == (b1, u_a, "owner")
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_rls_business_users_insert_impersonated_user_rejected(
    db_session: AsyncSession,
) -> None:
    b1 = str(uuid.uuid4())
    u_a = str(uuid.uuid4())
    u_b = str(uuid.uuid4())

    async with db_session.begin() as tx:
        try:
            await _insert_business(db_session, b1, "Target Store")

            await db_session.execute(text("SET LOCAL ROLE app_api;"))
            await db_session.execute(text(f"SET LOCAL app.current_user_id = '{u_a}';"))

            with pytest.raises(DBAPIError) as exc_without_biz:
                async with db_session.begin_nested():
                    await _insert_business_user(db_session, b1, u_b, "owner")
            _assert_sqlstate(exc_without_biz.value, "42501")

            await db_session.execute(text(f"SET LOCAL app.current_business_id = '{b1}';"))
            with pytest.raises(DBAPIError) as exc_with_biz:
                async with db_session.begin_nested():
                    await _insert_business_user(db_session, b1, u_b, "owner")
            _assert_sqlstate(exc_with_biz.value, "42501")
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_rls_business_users_insert_without_user_context_rejected(
    db_session: AsyncSession,
) -> None:
    b1 = str(uuid.uuid4())
    u_a = str(uuid.uuid4())

    async with db_session.begin() as tx:
        try:
            await _insert_business(db_session, b1, "No Context Store")

            await db_session.execute(text("SET LOCAL ROLE app_api;"))

            with pytest.raises(DBAPIError) as exc_unset:
                async with db_session.begin_nested():
                    await _insert_business_user(db_session, b1, u_a, "owner")
            _assert_sqlstate(exc_unset.value, "42501")

            await db_session.execute(text("SET LOCAL app.current_user_id = '';"))
            with pytest.raises(DBAPIError) as exc_empty:
                async with db_session.begin_nested():
                    await _insert_business_user(db_session, b1, u_a, "owner")
            _assert_sqlstate(exc_empty.value, "42501")
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_rls_business_users_insert_mismatched_business_id_rejected(
    db_session: AsyncSession,
) -> None:
    b1 = str(uuid.uuid4())
    b2 = str(uuid.uuid4())
    u_a = str(uuid.uuid4())

    async with db_session.begin() as tx:
        try:
            await _insert_business(db_session, b1, "Negocio 1")
            await _insert_business(db_session, b2, "Negocio 2")

            await db_session.execute(text("SET LOCAL ROLE app_api;"))
            await db_session.execute(text(f"SET LOCAL app.current_user_id = '{u_a}';"))
            await db_session.execute(text(f"SET LOCAL app.current_business_id = '{b1}';"))

            with pytest.raises(DBAPIError) as exc_info:
                async with db_session.begin_nested():
                    await _insert_business_user(db_session, b2, u_a, "owner")
            _assert_sqlstate(exc_info.value, "42501")
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_rls_business_users_update_hijack_rejected(db_session: AsyncSession) -> None:
    b1 = str(uuid.uuid4())
    b2 = str(uuid.uuid4())
    u_a = str(uuid.uuid4())

    async with db_session.begin() as tx:
        try:
            await _insert_business(db_session, b1, "Negocio 1")
            await _insert_business(db_session, b2, "Negocio 2")
            await _insert_business_user(db_session, b1, u_a, "owner")

            await db_session.execute(text("SET LOCAL ROLE app_api;"))
            await db_session.execute(text(f"SET LOCAL app.current_business_id = '{b1}';"))
            await db_session.execute(text(f"SET LOCAL app.current_user_id = '{u_a}';"))

            with pytest.raises(DBAPIError) as exc_filtered:
                async with db_session.begin_nested():
                    await db_session.execute(
                        text("UPDATE business_users SET business_id = :b2 WHERE user_id = :u_a;"),
                        {"b2": b2, "u_a": u_a},
                    )
            _assert_sqlstate(exc_filtered.value, "42501")

            with pytest.raises(DBAPIError) as exc_unfiltered:
                async with db_session.begin_nested():
                    await db_session.execute(
                        text("UPDATE business_users SET business_id = :b2;"),
                        {"b2": b2},
                    )
            _assert_sqlstate(exc_unfiltered.value, "42501")
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_app_api_role_exists_without_bypass_or_ownership(db_session: AsyncSession) -> None:
    async with db_session.begin() as tx:
        try:
            role_row = (
                await db_session.execute(
                    text(
                        """
                        SELECT rolsuper, rolbypassrls, rolcreaterole, rolcreatedb
                        FROM pg_roles
                        WHERE rolname = 'app_api';
                        """
                    )
                )
            ).one_or_none()
            assert role_row is not None, "Expected role app_api to exist"
            assert role_row[0] is False, "app_api must have rolsuper = false"
            assert role_row[1] is False, "app_api must have rolbypassrls = false"
            assert role_row[2] is False, "app_api must have rolcreaterole = false"
            assert role_row[3] is False, "app_api must have rolcreatedb = false"

            owners = (
                await db_session.execute(
                    text(
                        """
                        SELECT tablename, tableowner
                        FROM pg_tables
                        WHERE schemaname = 'public'
                          AND tablename IN ('businesses', 'business_users');
                        """
                    )
                )
            ).fetchall()
            assert len(owners) == 2
            for tablename, tableowner in owners:
                assert tableowner != "app_api", f"{tablename} must not be owned by app_api"

            rls_flags = (
                await db_session.execute(
                    text(
                        """
                        SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity
                        FROM pg_class c
                        JOIN pg_namespace n ON n.oid = c.relnamespace
                        WHERE n.nspname = 'public'
                          AND c.relname IN ('businesses', 'business_users')
                        ORDER BY c.relname;
                        """
                    )
                )
            ).fetchall()
            assert len(rls_flags) == 2
            for relname, relrowsecurity, relforcerowsecurity in rls_flags:
                assert relrowsecurity is True, f"{relname} must have ENABLE ROW LEVEL SECURITY"
                assert relforcerowsecurity is True, f"{relname} must have FORCE ROW LEVEL SECURITY"
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_app_api_performs_permitted_dml_under_rls(db_session: AsyncSession) -> None:
    b1 = str(uuid.uuid4())
    u_a = str(uuid.uuid4())

    async with db_session.begin() as tx:
        try:
            await db_session.execute(text("SET LOCAL ROLE app_api;"))
            await db_session.execute(text(f"SET LOCAL app.current_user_id = '{u_a}';"))
            await db_session.execute(text(f"SET LOCAL app.current_business_id = '{b1}';"))

            await _insert_business(db_session, b1, "Mi Negocio")
            biz_name = (
                await db_session.execute(
                    text("SELECT name FROM businesses WHERE id = :b1;"),
                    {"b1": b1},
                )
            ).scalar_one()
            assert biz_name == "Mi Negocio"

            await db_session.execute(
                text("UPDATE businesses SET name = 'Mi Negocio Editado' WHERE id = :b1;"),
                {"b1": b1},
            )
            updated_name = (
                await db_session.execute(
                    text("SELECT name FROM businesses WHERE id = :b1;"),
                    {"b1": b1},
                )
            ).scalar_one()
            assert updated_name == "Mi Negocio Editado"

            await _insert_business_user(db_session, b1, u_a, "owner")
            role = (
                await db_session.execute(
                    text(
                        "SELECT role FROM business_users "
                        "WHERE business_id = :b1 AND user_id = :u_a;"
                    ),
                    {"b1": b1, "u_a": u_a},
                )
            ).scalar_one()
            assert role == "owner"

            await db_session.execute(
                text(
                    "UPDATE business_users SET role = 'cashier' "
                    "WHERE business_id = :b1 AND user_id = :u_a;"
                ),
                {"b1": b1, "u_a": u_a},
            )
            updated_role = (
                await db_session.execute(
                    text(
                        "SELECT role FROM business_users "
                        "WHERE business_id = :b1 AND user_id = :u_a;"
                    ),
                    {"b1": b1, "u_a": u_a},
                )
            ).scalar_one()
            assert updated_role == "cashier"

            del_own = await db_session.execute(
                text("DELETE FROM business_users WHERE business_id = :b1 AND user_id = :u_a;"),
                {"b1": b1, "u_a": u_a},
            )
            assert del_own.rowcount == 1
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_app_api_cannot_bypass_rls_or_truncate(db_session: AsyncSession) -> None:
    b1 = str(uuid.uuid4())
    b2 = str(uuid.uuid4())
    u1 = str(uuid.uuid4())
    u2 = str(uuid.uuid4())

    async with db_session.begin() as tx:
        try:
            await _insert_business(db_session, b1, "Negocio 1")
            await _insert_business(db_session, b2, "Negocio 2")
            await _insert_business_user(db_session, b1, u1, "owner")
            await _insert_business_user(db_session, b2, u2, "owner")

            await db_session.execute(text("SET LOCAL ROLE app_api;"))
            await db_session.execute(text(f"SET LOCAL app.current_business_id = '{b1}';"))

            assert (
                await db_session.execute(
                    text("SELECT id FROM businesses WHERE id = :b2;"), {"b2": b2}
                )
            ).fetchall() == []
            assert (
                await db_session.execute(
                    text("SELECT user_id FROM business_users WHERE business_id = :b2;"),
                    {"b2": b2},
                )
            ).fetchall() == []

            upd_biz = await db_session.execute(
                text("UPDATE businesses SET name = 'Hijacked' WHERE id = :b2;"), {"b2": b2}
            )
            assert upd_biz.rowcount == 0
            upd_bu = await db_session.execute(
                text("UPDATE business_users SET role = 'cashier' WHERE business_id = :b2;"),
                {"b2": b2},
            )
            assert upd_bu.rowcount == 0

            del_biz = await db_session.execute(
                text("DELETE FROM businesses WHERE id = :b2;"), {"b2": b2}
            )
            assert del_biz.rowcount == 0
            del_bu = await db_session.execute(
                text("DELETE FROM business_users WHERE business_id = :b2;"), {"b2": b2}
            )
            assert del_bu.rowcount == 0

            # Unfiltered DELETE must only affect active tenant b1, never b2
            del_unfiltered = await db_session.execute(text("DELETE FROM business_users;"))
            assert del_unfiltered.rowcount == 1

            await db_session.execute(text("RESET ROLE;"))
            # app_runtime is NOBYPASSRLS; switch context to b2 to verify its row survived.
            await db_session.execute(text(f"SET LOCAL app.current_business_id = '{b2}';"))
            remaining_b2 = (
                await db_session.execute(
                    text("SELECT count(*) FROM business_users WHERE business_id = :b2;"),
                    {"b2": b2},
                )
            ).scalar_one()
            assert remaining_b2 == 1

            await db_session.execute(text("SET LOCAL ROLE app_api;"))

            with pytest.raises(DBAPIError) as exc_trunc_biz:
                async with db_session.begin_nested():
                    await db_session.execute(text("TRUNCATE businesses;"))
            _assert_sqlstate(exc_trunc_biz.value, "42501")

            with pytest.raises(DBAPIError) as exc_trunc_bu:
                async with db_session.begin_nested():
                    await db_session.execute(text("TRUNCATE business_users;"))
            _assert_sqlstate(exc_trunc_bu.value, "42501")
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_businesses_onboarding_insert_requires_user_and_matching_business_context(
    db_session: AsyncSession,
) -> None:
    b1 = str(uuid.uuid4())
    b2 = str(uuid.uuid4())
    u1 = str(uuid.uuid4())

    async with db_session.begin() as tx:
        try:
            await db_session.execute(text("SET LOCAL ROLE app_api;"))

            # Raw INSERT sin GUCs: el helper ahora setea contexto, así que se usa SQL directo
            # para verificar que la política rechaza correctamente cada caso negativo.
            raw_insert_business = text("""
                INSERT INTO businesses (id, name, country, timezone)
                VALUES (:id, :name, 'AR', 'America/Argentina/Buenos_Aires')
            """)

            # Sin app.current_user_id ni app.current_business_id -> 42501
            with pytest.raises(DBAPIError) as exc_no_ctx:
                async with db_session.begin_nested():
                    await db_session.execute(
                        raw_insert_business, {"id": b1, "name": "Sin Contexto"}
                    )
            _assert_sqlstate(exc_no_ctx.value, "42501")

            # Con app.current_user_id pero sin app.current_business_id -> 42501
            await db_session.execute(text(f"SET LOCAL app.current_user_id = '{u1}';"))
            with pytest.raises(DBAPIError) as exc_no_biz:
                async with db_session.begin_nested():
                    await db_session.execute(
                        raw_insert_business, {"id": b1, "name": "Sin Business"}
                    )
            _assert_sqlstate(exc_no_biz.value, "42501")

            # Con app.current_business_id distinto al id insertado -> 42501
            await db_session.execute(text(f"SET LOCAL app.current_business_id = '{b2}';"))
            with pytest.raises(DBAPIError) as exc_mismatch:
                async with db_session.begin_nested():
                    await db_session.execute(
                        raw_insert_business, {"id": b1, "name": "Mismatch Business"}
                    )
            _assert_sqlstate(exc_mismatch.value, "42501")

            # Con ambos GUCs válidos y coincidentes -> permitido
            await db_session.execute(text(f"SET LOCAL app.current_business_id = '{b1}';"))
            await _insert_business(db_session, b1, "Onboarding Valido")
            row = (
                await db_session.execute(
                    text("SELECT name FROM businesses WHERE id = :b1;"),
                    {"b1": b1},
                )
            ).scalar_one()
            assert row == "Onboarding Valido"
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_authenticated_cannot_access_or_truncate_tables(db_session: AsyncSession) -> None:
    async with db_session.begin() as tx:
        try:
            await db_session.execute(text("SET LOCAL ROLE authenticated;"))

            with pytest.raises(DBAPIError) as exc_sel_biz:
                async with db_session.begin_nested():
                    await db_session.execute(text("SELECT id FROM businesses LIMIT 1;"))
            _assert_sqlstate(exc_sel_biz.value, "42501")

            with pytest.raises(DBAPIError) as exc_trunc_biz:
                async with db_session.begin_nested():
                    await db_session.execute(text("TRUNCATE businesses;"))
            _assert_sqlstate(exc_trunc_biz.value, "42501")

            with pytest.raises(DBAPIError) as exc_trunc_bu:
                async with db_session.begin_nested():
                    await db_session.execute(text("TRUNCATE business_users;"))
            _assert_sqlstate(exc_trunc_bu.value, "42501")
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_rls_business_users_insert_without_business_context_rejected(
    db_session: AsyncSession,
) -> None:
    b1 = str(uuid.uuid4())
    u_a = str(uuid.uuid4())

    async with db_session.begin() as tx:
        try:
            await _insert_business(db_session, b1, "Target Store")

            await db_session.execute(text("SET LOCAL ROLE app_api;"))
            await db_session.execute(text(f"SET LOCAL app.current_user_id = '{u_a}';"))

            raw_insert_bu = text("""
                INSERT INTO business_users (business_id, user_id, role)
                VALUES (:b_id, :u_id, :role)
            """)

            # Limpiar current_business_id heredado del setup del helper (migración 0004 lo setea).
            await db_session.execute(text("SET LOCAL app.current_business_id = '';"))

            # app.current_business_id vacío debe rechazarse con 42501
            with pytest.raises(DBAPIError) as exc_unset:
                async with db_session.begin_nested():
                    await db_session.execute(
                        raw_insert_bu, {"b_id": b1, "u_id": u_a, "role": "owner"}
                    )
            _assert_sqlstate(exc_unset.value, "42501")

            # app.current_business_id vacío debe rechazarse con 42501
            await db_session.execute(text("SET LOCAL app.current_business_id = '';"))
            with pytest.raises(DBAPIError) as exc_empty:
                async with db_session.begin_nested():
                    await db_session.execute(
                        raw_insert_bu, {"b_id": b1, "u_id": u_a, "role": "owner"}
                    )
            _assert_sqlstate(exc_empty.value, "42501")
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_business_users_update_and_delete_blocked_for_cashier_role(
    db_session: AsyncSession,
) -> None:
    b1 = str(uuid.uuid4())
    u_owner = str(uuid.uuid4())
    u_cashier = str(uuid.uuid4())

    async with db_session.begin() as tx:
        try:
            await _insert_business(db_session, b1, "Tienda Roles")
            await _insert_business_user(db_session, b1, u_owner, "owner")
            await _insert_business_user(db_session, b1, u_cashier, "cashier")

            await db_session.execute(text("SET LOCAL ROLE app_api;"))
            await db_session.execute(text(f"SET LOCAL app.current_business_id = '{b1}';"))
            await db_session.execute(text(f"SET LOCAL app.current_user_id = '{u_cashier}';"))
            await db_session.execute(text("SET LOCAL app.current_user_role = 'cashier';"))

            upd = await db_session.execute(
                text("UPDATE business_users SET role = 'owner' WHERE user_id = :u;"),
                {"u": u_cashier},
            )
            assert upd.rowcount == 0

            dele = await db_session.execute(
                text("DELETE FROM business_users WHERE user_id = :u;"),
                {"u": u_owner},
            )
            assert dele.rowcount == 0
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_app_runtime_role_exists_with_nobypassrls_and_inherits_app_api(
    db_session: AsyncSession,
) -> None:
    b1 = str(uuid.uuid4())
    b2 = str(uuid.uuid4())

    async with db_session.begin() as tx:
        try:
            role_row = (
                await db_session.execute(
                    text(
                        """
                        SELECT
                            rolcanlogin,
                            rolsuper,
                            rolbypassrls,
                            rolcreatedb,
                            rolcreaterole,
                            pg_has_role('app_runtime', 'app_api', 'MEMBER') AS is_member
                        FROM pg_roles
                        WHERE rolname = 'app_runtime';
                        """
                    )
                )
            ).one_or_none()
            assert role_row is not None, "El rol app_runtime debe existir"
            assert role_row[0] is True
            assert role_row[1] is False
            assert role_row[2] is False
            assert role_row[3] is False
            assert role_row[4] is False
            assert role_row[5] is True

            await _insert_business(db_session, b1, "Negocio 1")
            await _insert_business(db_session, b2, "Negocio 2")

            # Incluso sin SET LOCAL ROLE app_api, app_runtime no puede saltarse RLS ni truncar
            await db_session.execute(text("SET LOCAL ROLE app_runtime;"))
            await db_session.execute(text(f"SET LOCAL app.current_business_id = '{b1}';"))

            rows = (
                await db_session.execute(
                    text("SELECT id FROM businesses WHERE id = :b2;"),
                    {"b2": b2},
                )
            ).fetchall()
            assert rows == []

            with pytest.raises(DBAPIError) as exc_trunc:
                async with db_session.begin_nested():
                    await db_session.execute(text("TRUNCATE businesses;"))
            _assert_sqlstate(exc_trunc.value, "42501")
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_businesses_updated_at_trigger_updates_on_update(db_session: AsyncSession) -> None:
    b1 = str(uuid.uuid4())
    async with db_session.begin() as tx:
        try:
            await _insert_business(db_session, b1, "Original")
            initial_ts = (
                await db_session.execute(
                    text("SELECT updated_at FROM businesses WHERE id = :b1;"),
                    {"b1": b1},
                )
            ).scalar_one()

            await db_session.execute(
                text("UPDATE businesses SET name = 'Actualizado' WHERE id = :b1;"),
                {"b1": b1},
            )
            new_ts = (
                await db_session.execute(
                    text("SELECT updated_at FROM businesses WHERE id = :b1;"),
                    {"b1": b1},
                )
            ).scalar_one()
            assert new_ts > initial_ts
        finally:
            await tx.rollback()
