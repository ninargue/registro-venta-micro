import uuid
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.catalogo


def _assert_sqlstate(exc: DBAPIError, expected_sqlstate: str) -> None:
    orig = exc.orig
    sqlstate = getattr(orig, "sqlstate", None) or getattr(
        getattr(orig, "__cause__", None), "sqlstate", None
    )
    assert sqlstate == expected_sqlstate, (
        f"Expected SQLSTATE {expected_sqlstate}, got {sqlstate!r} ({exc})"
    )


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


async def _insert_product(
    db_session: AsyncSession,
    *,
    business_id: str,
    name: str = "Producto Test",
    sale_price: Decimal = Decimal("100.00"),
    cost_price: Decimal = Decimal("50.00"),
    stock: Decimal = Decimal("10.00"),
    code: str | None = None,
    is_active: bool = True,
    product_id: str | None = None,
) -> str:
    pid = product_id or str(uuid.uuid4())
    await db_session.execute(text(f"SET LOCAL app.current_business_id = '{business_id}';"))
    await db_session.execute(
        text(
            """
            INSERT INTO products (
                id, business_id, code, name, sale_price, cost_price, stock, is_active
            )
            VALUES (
                :id, :business_id, :code, :name, :sale_price, :cost_price, :stock, :is_active
            )
            """
        ),
        {
            "id": pid,
            "business_id": business_id,
            "code": code,
            "name": name,
            "sale_price": sale_price,
            "cost_price": cost_price,
            "stock": stock,
            "is_active": is_active,
        },
    )
    return pid


@pytest.mark.asyncio
async def test_insert_product_valid_with_defaults(db_session: AsyncSession) -> None:
    business_id = str(uuid.uuid4())
    async with db_session.begin() as tx:
        try:
            await _insert_business(db_session, business_id, "Almacen Don Pepe")

            result = await db_session.execute(
                text(
                    """
                    INSERT INTO products (business_id, name, sale_price)
                    VALUES (:business_id, :name, :sale_price)
                    RETURNING id, business_id, code, name, sale_price, cost_price,
                              stock, is_active, created_at, updated_at
                    """
                ),
                {
                    "business_id": business_id,
                    "name": "Yerba Mate 1kg",
                    "sale_price": Decimal("3500.50"),
                },
            )
            row = result.mappings().one()
            assert uuid.UUID(str(row["id"]))
            assert str(row["business_id"]) == business_id
            assert row["code"] is None
            assert row["name"] == "Yerba Mate 1kg"
            assert isinstance(row["sale_price"], Decimal)
            assert row["sale_price"] == Decimal("3500.50")
            assert isinstance(row["cost_price"], Decimal)
            assert row["cost_price"] == Decimal("0.00")
            assert isinstance(row["stock"], Decimal)
            assert row["stock"] == Decimal("0.00")
            assert row["is_active"] is True
            assert row["created_at"] is not None
            assert row["updated_at"] is not None

            explicit_id = await _insert_product(
                db_session,
                business_id=business_id,
                code="SKU-001",
                name="Cafe Molido 500g",
                sale_price=Decimal("4200.00"),
                cost_price=Decimal("2800.25"),
                stock=Decimal("15.50"),
                is_active=True,
            )
            explicit_row = (
                (
                    await db_session.execute(
                        text(
                            """
                        SELECT code, sale_price, cost_price, stock, is_active
                        FROM products
                        WHERE id = :id
                        """
                        ),
                        {"id": explicit_id},
                    )
                )
                .mappings()
                .one()
            )
            assert explicit_row["code"] == "SKU-001"
            assert explicit_row["sale_price"] == Decimal("4200.00")
            assert explicit_row["cost_price"] == Decimal("2800.25")
            assert explicit_row["stock"] == Decimal("15.50")
            assert explicit_row["is_active"] is True
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_products_exact_decimal_precision_without_float(db_session: AsyncSession) -> None:
    business_id = str(uuid.uuid4())
    async with db_session.begin() as tx:
        try:
            cols = (
                (
                    await db_session.execute(
                        text(
                            """
                        SELECT column_name, data_type, numeric_precision, numeric_scale
                        FROM information_schema.columns
                        WHERE table_schema = 'public'
                          AND table_name = 'products'
                          AND column_name IN ('sale_price', 'cost_price', 'stock')
                        ORDER BY column_name
                        """
                        )
                    )
                )
                .mappings()
                .all()
            )

            assert [c["column_name"] for c in cols] == ["cost_price", "sale_price", "stock"]
            for col in cols:
                assert col["data_type"] == "numeric"
                assert col["numeric_precision"] == 12
                assert col["numeric_scale"] == 2

            await _insert_business(db_session, business_id, "Libreria Exacta")
            pid = await _insert_product(
                db_session,
                business_id=business_id,
                name="Lapicera Azul",
                sale_price=Decimal("19.99"),
                cost_price=Decimal("0.10"),
                stock=Decimal("0.20"),
            )
            total = (
                await db_session.execute(
                    text("SELECT cost_price + stock FROM products WHERE id = :id"),
                    {"id": pid},
                )
            ).scalar_one()
            assert isinstance(total, Decimal)
            assert total == Decimal("0.30")
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_insert_product_rejects_nulls_on_mandatory_attributes(
    db_session: AsyncSession,
) -> None:
    business_id = str(uuid.uuid4())
    async with db_session.begin() as tx:
        try:
            await _insert_business(db_session, business_id, "Kiosco Nulls")

            null_cases = [
                (
                    "INSERT INTO products (business_id, name, sale_price) "
                    "VALUES (NULL, 'Prod', 10.00)",
                    {},
                ),
                (
                    "INSERT INTO products (business_id, name, sale_price) "
                    "VALUES (:b_id, NULL, 10.00)",
                    {"b_id": business_id},
                ),
                (
                    "INSERT INTO products (business_id, name, sale_price) "
                    "VALUES (:b_id, 'Prod', NULL)",
                    {"b_id": business_id},
                ),
                (
                    "INSERT INTO products (business_id, name, sale_price, cost_price) "
                    "VALUES (:b_id, 'Prod', 10.00, NULL)",
                    {"b_id": business_id},
                ),
                (
                    "INSERT INTO products (business_id, name, sale_price, stock) "
                    "VALUES (:b_id, 'Prod', 10.00, NULL)",
                    {"b_id": business_id},
                ),
                (
                    "INSERT INTO products (business_id, name, sale_price, is_active) "
                    "VALUES (:b_id, 'Prod', 10.00, NULL)",
                    {"b_id": business_id},
                ),
                (
                    "INSERT INTO products (business_id, name, sale_price, created_at) "
                    "VALUES (:b_id, 'Prod', 10.00, NULL)",
                    {"b_id": business_id},
                ),
                (
                    "INSERT INTO products (business_id, name, sale_price, updated_at) "
                    "VALUES (:b_id, 'Prod', 10.00, NULL)",
                    {"b_id": business_id},
                ),
            ]
            for sql, params in null_cases:
                with pytest.raises(IntegrityError) as exc_info:
                    async with db_session.begin_nested():
                        await db_session.execute(text(sql), params)
                _assert_sqlstate(exc_info.value, "23502")
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_insert_product_rejects_orphan_business_id(db_session: AsyncSession) -> None:
    non_existent_business_id = str(uuid.uuid4())
    with pytest.raises(IntegrityError) as exc_info:
        async with db_session.begin():
            await _insert_product(
                db_session,
                business_id=non_existent_business_id,
                name="Huerfano",
                sale_price=Decimal("100.00"),
            )
    _assert_sqlstate(exc_info.value, "23503")


@pytest.mark.asyncio
async def test_products_cascade_delete_when_business_removed(db_session: AsyncSession) -> None:
    business_id = str(uuid.uuid4())
    async with db_session.begin() as tx:
        try:
            await _insert_business(db_session, business_id, "Negocio Efimero")
            await _insert_product(
                db_session, business_id=business_id, name="Prod 1", sale_price=Decimal("10.00")
            )
            await _insert_product(
                db_session, business_id=business_id, name="Prod 2", sale_price=Decimal("20.00")
            )

            await db_session.execute(
                text("DELETE FROM businesses WHERE id = :id"),
                {"id": business_id},
            )
            remaining = (
                await db_session.execute(
                    text("SELECT count(*) FROM products WHERE business_id = :b_id"),
                    {"b_id": business_id},
                )
            ).scalar_one()
            assert remaining == 0
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_products_rejects_blank_name_or_blank_non_null_code(
    db_session: AsyncSession,
) -> None:
    business_id = str(uuid.uuid4())
    async with db_session.begin() as tx:
        try:
            await _insert_business(db_session, business_id, "Tienda Checks")
            pid = await _insert_product(
                db_session,
                business_id=business_id,
                name="Nombre Valido",
                code="VALID-1",
                sale_price=Decimal("50.00"),
            )

            for bad_name in ("", "   "):
                with pytest.raises(IntegrityError) as exc_ins_name:
                    async with db_session.begin_nested():
                        await _insert_product(
                            db_session,
                            business_id=business_id,
                            name=bad_name,
                            sale_price=Decimal("10.00"),
                        )
                _assert_sqlstate(exc_ins_name.value, "23514")

                with pytest.raises(IntegrityError) as exc_upd_name:
                    async with db_session.begin_nested():
                        await db_session.execute(
                            text("UPDATE products SET name = :name WHERE id = :id"),
                            {"name": bad_name, "id": pid},
                        )
                _assert_sqlstate(exc_upd_name.value, "23514")

            for bad_code in ("", "  "):
                with pytest.raises(IntegrityError) as exc_ins_code:
                    async with db_session.begin_nested():
                        await _insert_product(
                            db_session,
                            business_id=business_id,
                            name="Otro Producto",
                            code=bad_code,
                            sale_price=Decimal("10.00"),
                        )
                _assert_sqlstate(exc_ins_code.value, "23514")

                with pytest.raises(IntegrityError) as exc_upd_code:
                    async with db_session.begin_nested():
                        await db_session.execute(
                            text("UPDATE products SET code = :code WHERE id = :id"),
                            {"code": bad_code, "id": pid},
                        )
                _assert_sqlstate(exc_upd_code.value, "23514")
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_products_rejects_zero_or_negative_sale_price(db_session: AsyncSession) -> None:
    business_id = str(uuid.uuid4())
    async with db_session.begin() as tx:
        try:
            await _insert_business(db_session, business_id, "Tienda Precios")
            pid = await _insert_product(
                db_session,
                business_id=business_id,
                name="Producto Precio",
                sale_price=Decimal("10.00"),
            )

            for invalid_price in (Decimal("0.00"), Decimal("-5.00")):
                with pytest.raises(IntegrityError) as exc_ins:
                    async with db_session.begin_nested():
                        await _insert_product(
                            db_session,
                            business_id=business_id,
                            name="Precio Invalido",
                            sale_price=invalid_price,
                        )
                _assert_sqlstate(exc_ins.value, "23514")

                with pytest.raises(IntegrityError) as exc_upd:
                    async with db_session.begin_nested():
                        await db_session.execute(
                            text("UPDATE products SET sale_price = :price WHERE id = :id"),
                            {"price": invalid_price, "id": pid},
                        )
                _assert_sqlstate(exc_upd.value, "23514")
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_products_rejects_negative_cost_price_allows_zero(
    db_session: AsyncSession,
) -> None:
    business_id = str(uuid.uuid4())
    async with db_session.begin() as tx:
        try:
            await _insert_business(db_session, business_id, "Tienda Costos")
            pid = await _insert_product(
                db_session,
                business_id=business_id,
                name="Costo Cero",
                sale_price=Decimal("15.00"),
                cost_price=Decimal("0.00"),
            )
            stored_cost = (
                await db_session.execute(
                    text("SELECT cost_price FROM products WHERE id = :id"),
                    {"id": pid},
                )
            ).scalar_one()
            assert stored_cost == Decimal("0.00")

            with pytest.raises(IntegrityError) as exc_ins:
                async with db_session.begin_nested():
                    await _insert_product(
                        db_session,
                        business_id=business_id,
                        name="Costo Negativo",
                        sale_price=Decimal("15.00"),
                        cost_price=Decimal("-0.01"),
                    )
            _assert_sqlstate(exc_ins.value, "23514")

            with pytest.raises(IntegrityError) as exc_upd:
                async with db_session.begin_nested():
                    await db_session.execute(
                        text("UPDATE products SET cost_price = -0.01 WHERE id = :id"),
                        {"id": pid},
                    )
            _assert_sqlstate(exc_upd.value, "23514")
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_products_atomic_stock_deduction_allows_transient_negative(
    db_session: AsyncSession,
) -> None:
    business_id = str(uuid.uuid4())
    async with db_session.begin() as tx:
        try:
            await _insert_business(db_session, business_id, "Mostrador Rapido")
            pid = await _insert_product(
                db_session,
                business_id=business_id,
                name="Gaseosa 500ml",
                sale_price=Decimal("1200.00"),
                stock=Decimal("2.00"),
            )

            await db_session.execute(
                text("UPDATE products SET stock = stock - 3.00 WHERE id = :id"),
                {"id": pid},
            )
            new_stock = (
                await db_session.execute(
                    text("SELECT stock FROM products WHERE id = :id"),
                    {"id": pid},
                )
            ).scalar_one()
            assert isinstance(new_stock, Decimal)
            assert new_stock == Decimal("-1.00")
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_products_allows_multiple_null_codes_in_same_business(
    db_session: AsyncSession,
) -> None:
    business_id = str(uuid.uuid4())
    async with db_session.begin() as tx:
        try:
            await _insert_business(db_session, business_id, "Panaderia Sin SKU")
            p1 = await _insert_product(
                db_session,
                business_id=business_id,
                name="Pan Casero",
                code=None,
                sale_price=Decimal("800.00"),
            )
            p2 = await _insert_product(
                db_session,
                business_id=business_id,
                name="Medialuna",
                code=None,
                sale_price=Decimal("300.00"),
            )
            assert p1 != p2
            count_nulls = (
                await db_session.execute(
                    text(
                        "SELECT count(*) FROM products WHERE business_id = :b_id AND code IS NULL"
                    ),
                    {"b_id": business_id},
                )
            ).scalar_one()
            assert count_nulls == 2
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_products_rejects_duplicate_non_null_code_in_same_business(
    db_session: AsyncSession,
) -> None:
    business_id = str(uuid.uuid4())
    async with db_session.begin() as tx:
        try:
            await _insert_business(db_session, business_id, "Ferreteria SKU")
            await _insert_product(
                db_session,
                business_id=business_id,
                name="Tornillo A",
                code="SKU-001",
                sale_price=Decimal("10.00"),
            )
            p2 = await _insert_product(
                db_session,
                business_id=business_id,
                name="Tornillo B",
                code="SKU-002",
                sale_price=Decimal("20.00"),
            )

            with pytest.raises(IntegrityError) as exc_ins:
                async with db_session.begin_nested():
                    await _insert_product(
                        db_session,
                        business_id=business_id,
                        name="Tornillo Duplicado",
                        code="SKU-001",
                        sale_price=Decimal("15.00"),
                    )
            _assert_sqlstate(exc_ins.value, "23505")

            with pytest.raises(IntegrityError) as exc_upd:
                async with db_session.begin_nested():
                    await db_session.execute(
                        text("UPDATE products SET code = 'SKU-001' WHERE id = :id"),
                        {"id": p2},
                    )
            _assert_sqlstate(exc_upd.value, "23505")
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_products_allows_same_code_across_distinct_businesses(
    db_session: AsyncSession,
) -> None:
    b1 = str(uuid.uuid4())
    b2 = str(uuid.uuid4())
    async with db_session.begin() as tx:
        try:
            await _insert_business(db_session, b1, "Comercio A")
            await _insert_business(db_session, b2, "Comercio B")

            p1 = await _insert_product(
                db_session,
                business_id=b1,
                name="Agua 500ml",
                code="SKU-001",
                sale_price=Decimal("500.00"),
            )
            p2 = await _insert_product(
                db_session,
                business_id=b2,
                name="Agua 500ml",
                code="SKU-001",
                sale_price=Decimal("550.00"),
            )
            assert p1 != p2
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_products_soft_deactivation_preserves_row_and_advances_updated_at(
    db_session: AsyncSession,
) -> None:
    business_id = str(uuid.uuid4())
    async with db_session.begin() as tx:
        try:
            await _insert_business(db_session, business_id, "Tienda Baja Logica")
            pid = await _insert_product(
                db_session,
                business_id=business_id,
                name="Producto Activo",
                sale_price=Decimal("100.00"),
                stock=Decimal("5.00"),
            )
            ts_0 = (
                await db_session.execute(
                    text("SELECT updated_at FROM products WHERE id = :id"),
                    {"id": pid},
                )
            ).scalar_one()

            await db_session.execute(
                text("UPDATE products SET is_active = false WHERE id = :id"),
                {"id": pid},
            )
            row_after_deact = (
                (
                    await db_session.execute(
                        text("SELECT is_active, updated_at FROM products WHERE id = :id"),
                        {"id": pid},
                    )
                )
                .mappings()
                .one()
            )
            assert row_after_deact["is_active"] is False
            ts_1 = row_after_deact["updated_at"]
            assert ts_1 > ts_0

            await db_session.execute(
                text("UPDATE products SET sale_price = 120.00 WHERE id = :id"),
                {"id": pid},
            )
            ts_2 = (
                await db_session.execute(
                    text("SELECT updated_at FROM products WHERE id = :id"),
                    {"id": pid},
                )
            ).scalar_one()
            assert ts_2 > ts_1
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_rls_products_authorized_tenant_crud_under_app_runtime(
    db_session: AsyncSession,
) -> None:
    b1 = str(uuid.uuid4())
    async with db_session.begin() as tx:
        try:
            await _insert_business(db_session, b1, "Tenant Autorizado")

            await db_session.execute(text("SET LOCAL ROLE app_runtime;"))
            await db_session.execute(text(f"SET LOCAL app.current_business_id = '{b1}';"))

            pid = await _insert_product(
                db_session,
                business_id=b1,
                name="Producto Propio",
                code="PROP-1",
                sale_price=Decimal("250.00"),
            )

            rows = (
                (
                    await db_session.execute(
                        text("SELECT id, name, sale_price FROM products WHERE id = :id"),
                        {"id": pid},
                    )
                )
                .mappings()
                .all()
            )
            assert len(rows) == 1
            assert rows[0]["name"] == "Producto Propio"
            assert rows[0]["sale_price"] == Decimal("250.00")

            upd = await db_session.execute(
                text("UPDATE products SET sale_price = 300.00 WHERE id = :id"),
                {"id": pid},
            )
            assert upd.rowcount == 1

            dele = await db_session.execute(
                text("DELETE FROM products WHERE id = :id"),
                {"id": pid},
            )
            assert dele.rowcount == 1
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_rls_products_cross_tenant_select_update_delete_blocked(
    db_session: AsyncSession,
) -> None:
    b1 = str(uuid.uuid4())
    b2 = str(uuid.uuid4())
    async with db_session.begin() as tx:
        try:
            await _insert_business(db_session, b1, "Tenant A")
            await _insert_business(db_session, b2, "Tenant B")
            p1 = await _insert_product(
                db_session, business_id=b1, name="Prod A", sale_price=Decimal("10.00")
            )
            p2 = await _insert_product(
                db_session, business_id=b2, name="Prod B", sale_price=Decimal("20.00")
            )

            await db_session.execute(text("SET LOCAL ROLE app_runtime;"))
            await db_session.execute(text(f"SET LOCAL app.current_business_id = '{b1}';"))

            visible_ids = [
                str(r[0])
                for r in (await db_session.execute(text("SELECT id FROM products;"))).fetchall()
            ]
            assert visible_ids == [p1]

            cross_filtered = (
                await db_session.execute(
                    text("SELECT id FROM products WHERE business_id = :b2;"),
                    {"b2": b2},
                )
            ).fetchall()
            assert cross_filtered == []

            upd_b2 = await db_session.execute(
                text("UPDATE products SET name = 'Hijacked' WHERE id = :p2;"),
                {"p2": p2},
            )
            assert upd_b2.rowcount == 0

            del_b2 = await db_session.execute(
                text("DELETE FROM products WHERE id = :p2;"),
                {"p2": p2},
            )
            assert del_b2.rowcount == 0

            # Unfiltered DELETE must only affect tenant A, leaving tenant B intact
            del_unfiltered = await db_session.execute(text("DELETE FROM products;"))
            assert del_unfiltered.rowcount == 1

            await db_session.execute(text("RESET ROLE;"))
            remaining_b2 = (
                await db_session.execute(
                    text("SELECT name FROM products WHERE id = :p2;"),
                    {"p2": p2},
                )
            ).scalar_one()
            assert remaining_b2 == "Prod B"
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_rls_products_cross_tenant_insert_and_update_hijack_rejected(
    db_session: AsyncSession,
) -> None:
    b1 = str(uuid.uuid4())
    b2 = str(uuid.uuid4())
    async with db_session.begin() as tx:
        try:
            await _insert_business(db_session, b1, "Tenant A")
            await _insert_business(db_session, b2, "Tenant B")
            p1 = await _insert_product(
                db_session, business_id=b1, name="Prod A", sale_price=Decimal("10.00")
            )

            await db_session.execute(text("SET LOCAL ROLE app_runtime;"))
            await db_session.execute(text(f"SET LOCAL app.current_business_id = '{b1}';"))

            with pytest.raises(DBAPIError) as exc_ins:
                async with db_session.begin_nested():
                    await db_session.execute(
                        text(
                            "INSERT INTO products (business_id, name, sale_price) "
                            "VALUES (:b_id, :name, :price)"
                        ),
                        {"b_id": b2, "name": "Cross Tenant Insert", "price": Decimal("50.00")},
                    )
            _assert_sqlstate(exc_ins.value, "42501")

            with pytest.raises(DBAPIError) as exc_upd_filtered:
                async with db_session.begin_nested():
                    await db_session.execute(
                        text("UPDATE products SET business_id = :b2 WHERE id = :p1;"),
                        {"b2": b2, "p1": p1},
                    )
            _assert_sqlstate(exc_upd_filtered.value, "42501")

            with pytest.raises(DBAPIError) as exc_upd_unfiltered:
                async with db_session.begin_nested():
                    await db_session.execute(
                        text("UPDATE products SET business_id = :b2;"),
                        {"b2": b2},
                    )
            _assert_sqlstate(exc_upd_unfiltered.value, "42501")
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_rls_products_without_tenant_context_returns_empty_and_blocks_insert(
    db_session: AsyncSession,
) -> None:
    b1 = str(uuid.uuid4())
    async with db_session.begin() as tx:
        try:
            await _insert_business(db_session, b1, "Tenant Con Datos")
            await _insert_product(
                db_session, business_id=b1, name="Prod Existente", sale_price=Decimal("10.00")
            )

            await db_session.execute(text("SET LOCAL ROLE app_runtime;"))
            await db_session.execute(text("SET LOCAL app.current_business_id = '';"))

            for ctx_sql in (None, "SET LOCAL app.current_business_id = '';"):
                if ctx_sql is not None:
                    await db_session.execute(text(ctx_sql))

                assert (await db_session.execute(text("SELECT id FROM products;"))).fetchall() == []
                assert (
                    await db_session.execute(text("UPDATE products SET name = 'NoCtx';"))
                ).rowcount == 0
                assert (await db_session.execute(text("DELETE FROM products;"))).rowcount == 0

                with pytest.raises(DBAPIError) as exc_ins:
                    async with db_session.begin_nested():
                        await db_session.execute(
                            text(
                                "INSERT INTO products (business_id, name, sale_price) "
                                "VALUES (:b_id, :name, :price)"
                            ),
                            {"b_id": b1, "name": "Sin Contexto", "price": Decimal("10.00")},
                        )
                _assert_sqlstate(exc_ins.value, "42501")
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_products_metadata_forced_rls_and_non_privileged_ownership(
    db_session: AsyncSession,
) -> None:
    async with db_session.begin() as tx:
        try:
            rls_row = (
                await db_session.execute(
                    text(
                        """
                        SELECT c.relrowsecurity, c.relforcerowsecurity
                        FROM pg_class c
                        JOIN pg_namespace n ON n.oid = c.relnamespace
                        WHERE n.nspname = 'public' AND c.relname = 'products';
                        """
                    )
                )
            ).one_or_none()
            assert rls_row is not None, "Table public.products must exist"
            assert rls_row[0] is True, "products must have ENABLE ROW LEVEL SECURITY"
            assert rls_row[1] is True, "products must have FORCE ROW LEVEL SECURITY"

            owner = (
                await db_session.execute(
                    text(
                        """
                        SELECT tableowner
                        FROM pg_tables
                        WHERE schemaname = 'public' AND tablename = 'products';
                        """
                    )
                )
            ).scalar_one()
            assert owner not in ("app_api", "app_runtime")

            roles = (
                await db_session.execute(
                    text(
                        """
                        SELECT rolname, rolsuper, rolbypassrls
                        FROM pg_roles
                        WHERE rolname IN ('app_api', 'app_runtime')
                        ORDER BY rolname;
                        """
                    )
                )
            ).fetchall()
            assert len(roles) == 2
            for rolname, rolsuper, rolbypassrls in roles:
                assert rolsuper is False, f"{rolname} must have rolsuper = false"
                assert rolbypassrls is False, f"{rolname} must have rolbypassrls = false"

            grants = {
                row[0]
                for row in (
                    await db_session.execute(
                        text(
                            """
                            SELECT privilege_type
                            FROM information_schema.role_table_grants
                            WHERE table_schema = 'public'
                              AND table_name = 'products'
                              AND grantee = 'app_api';
                            """
                        )
                    )
                ).fetchall()
            }
            assert grants == {"SELECT", "INSERT", "UPDATE", "DELETE"}

            public_grants = (
                await db_session.execute(
                    text(
                        """
                        SELECT grantee, privilege_type
                        FROM information_schema.role_table_grants
                        WHERE table_schema = 'public'
                          AND table_name = 'products'
                          AND grantee IN ('PUBLIC', 'anon', 'authenticated');
                        """
                    )
                )
            ).fetchall()
            assert public_grants == []
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_app_runtime_cannot_truncate_products(db_session: AsyncSession) -> None:
    b1 = str(uuid.uuid4())
    async with db_session.begin() as tx:
        try:
            await _insert_business(db_session, b1, "Tenant Truncate")
            await _insert_product(
                db_session, business_id=b1, name="No Truncar", sale_price=Decimal("10.00")
            )

            await db_session.execute(text("SET LOCAL ROLE app_runtime;"))
            await db_session.execute(text(f"SET LOCAL app.current_business_id = '{b1}';"))

            with pytest.raises(DBAPIError) as exc_trunc:
                async with db_session.begin_nested():
                    await db_session.execute(text("TRUNCATE products;"))
            _assert_sqlstate(exc_trunc.value, "42501")
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_authenticated_and_anon_cannot_access_or_truncate_products(
    db_session: AsyncSession,
) -> None:
    b1 = str(uuid.uuid4())
    async with db_session.begin() as tx:
        try:
            await _insert_business(db_session, b1, "Negocio Privado")
            pid = await _insert_product(
                db_session, business_id=b1, name="Secreto", sale_price=Decimal("99.00")
            )

            for role in ("authenticated", "anon"):
                role_switched = False
                try:
                    async with db_session.begin_nested():
                        await db_session.execute(text(f"SET LOCAL ROLE {role};"))
                    role_switched = True
                except DBAPIError as exc_role:
                    orig = exc_role.orig
                    sqlstate = getattr(orig, "sqlstate", None) or getattr(
                        getattr(orig, "__cause__", None), "sqlstate", None
                    )
                    assert sqlstate in ("42501", "42704"), (
                        f"Expected 42501/42704 switching to role {role!r}, got {sqlstate!r}: {exc_role}"
                    )

                if not role_switched:
                    continue

                statements = [
                    ("SELECT id FROM products LIMIT 1;", {}),
                    (
                        "INSERT INTO products (business_id, name, sale_price) "
                        "VALUES (:b_id, 'Hack', 1.00);",
                        {"b_id": b1},
                    ),
                    ("UPDATE products SET name = 'Hack' WHERE id = :pid;", {"pid": pid}),
                    ("DELETE FROM products WHERE id = :pid;", {"pid": pid}),
                    ("TRUNCATE products;", {}),
                ]
                for sql, params in statements:
                    with pytest.raises(DBAPIError) as exc_info:
                        async with db_session.begin_nested():
                            await db_session.execute(text(sql), params)
                    _assert_sqlstate(exc_info.value, "42501")

                await db_session.execute(text("RESET ROLE;"))
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_products_composite_unique_business_id_id_supports_composite_fk(
    db_session: AsyncSession,
) -> None:
    b1 = str(uuid.uuid4())
    b2 = str(uuid.uuid4())
    async with db_session.begin() as tx:
        try:
            constraint_row = (
                (
                    await db_session.execute(
                        text(
                            """
                            SELECT
                                c.conname,
                                c.contype::text AS contype,
                                pg_get_constraintdef(c.oid) AS condef
                            FROM pg_constraint c
                            JOIN pg_class t ON t.oid = c.conrelid
                            JOIN pg_namespace n ON n.oid = t.relnamespace
                            WHERE n.nspname = 'public'
                              AND t.relname = 'products'
                              AND c.conname = 'uq_products_business_id_id';
                            """
                        )
                    )
                )
                .mappings()
                .one_or_none()
            )
            assert constraint_row is not None, "uq_products_business_id_id must exist on products"
            assert constraint_row["contype"] == "u"
            assert "UNIQUE (business_id, id)" in constraint_row["condef"]

            await _insert_business(db_session, b1, "Comercio FK A")
            await _insert_business(db_session, b2, "Comercio FK B")
            p1 = await _insert_product(
                db_session, business_id=b1, name="Prod FK", sale_price=Decimal("50.00")
            )

            await db_session.execute(
                text(
                    """
                    CREATE TABLE public.tmp_composite_fk_check (
                        business_id uuid NOT NULL,
                        product_id uuid NOT NULL,
                        FOREIGN KEY (business_id, product_id)
                            REFERENCES public.products (business_id, id)
                    );
                    """
                )
            )
            await db_session.execute(
                text(
                    """
                    INSERT INTO public.tmp_composite_fk_check (business_id, product_id)
                    VALUES (:b_id, :p_id);
                    """
                ),
                {"b_id": b1, "p_id": p1},
            )

            with pytest.raises(IntegrityError) as exc_cross_fk:
                async with db_session.begin_nested():
                    await db_session.execute(
                        text(
                            """
                            INSERT INTO public.tmp_composite_fk_check (business_id, product_id)
                            VALUES (:b_id, :p_id);
                            """
                        ),
                        {"b_id": b2, "p_id": p1},
                    )
            _assert_sqlstate(exc_cross_fk.value, "23503")
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_products_primary_key_rejects_duplicate_id(db_session: AsyncSession) -> None:
    b1 = str(uuid.uuid4())
    b2 = str(uuid.uuid4())
    shared_product_id = str(uuid.uuid4())
    async with db_session.begin() as tx:
        try:
            await _insert_business(db_session, b1, "Comercio PK A")
            await _insert_business(db_session, b2, "Comercio PK B")

            await _insert_product(
                db_session,
                business_id=b1,
                product_id=shared_product_id,
                name="Producto Original",
                sale_price=Decimal("100.00"),
            )

            for target_business in (b1, b2):
                with pytest.raises(IntegrityError) as exc_pk:
                    async with db_session.begin_nested():
                        await _insert_product(
                            db_session,
                            business_id=target_business,
                            product_id=shared_product_id,
                            name="Producto ID Duplicado",
                            sale_price=Decimal("200.00"),
                        )
                _assert_sqlstate(exc_pk.value, "23505")
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_products_partial_unique_code_index_metadata(db_session: AsyncSession) -> None:
    async with db_session.begin() as tx:
        try:
            idx_row = (
                (
                    await db_session.execute(
                        text(
                            """
                            SELECT
                                i.indisunique,
                                i.indpred IS NOT NULL AS has_predicate,
                                pg_get_expr(i.indpred, i.indrelid) AS predicate_expr
                            FROM pg_index i
                            JOIN pg_class idx ON idx.oid = i.indexrelid
                            JOIN pg_class tbl ON tbl.oid = i.indrelid
                            JOIN pg_namespace ns ON ns.oid = tbl.relnamespace
                            WHERE ns.nspname = 'public'
                              AND tbl.relname = 'products'
                              AND idx.relname = 'uq_products_business_id_code';
                            """
                        )
                    )
                )
                .mappings()
                .one_or_none()
            )
            assert idx_row is not None, "uq_products_business_id_code index must exist"
            assert idx_row["indisunique"] is True
            assert idx_row["has_predicate"] is True
            assert "code IS NOT NULL" in idx_row["predicate_expr"]
        finally:
            await tx.rollback()
