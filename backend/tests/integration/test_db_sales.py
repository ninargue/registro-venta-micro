import uuid
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession


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
    product_id: str | None = None,
) -> str:
    pid = product_id or str(uuid.uuid4())
    await db_session.execute(
        text(
            """
            INSERT INTO products (
                id, business_id, name, sale_price, cost_price, stock, is_active
            )
            VALUES (
                :id, :business_id, :name, :sale_price, :cost_price, :stock, true
            )
            """
        ),
        {
            "id": pid,
            "business_id": business_id,
            "name": name,
            "sale_price": sale_price,
            "cost_price": cost_price,
            "stock": stock,
        },
    )
    return pid


async def _insert_sale(
    db_session: AsyncSession,
    *,
    business_id: str,
    client_id: str | None = None,
    total_amount: Decimal = Decimal("100.00"),
    sale_id: str | None = None,
) -> str:
    sid = sale_id or str(uuid.uuid4())
    cid = client_id or str(uuid.uuid4())
    await db_session.execute(
        text(
            """
            INSERT INTO sales (id, business_id, client_id, total_amount)
            VALUES (:id, :business_id, :client_id, :total_amount)
            """
        ),
        {
            "id": sid,
            "business_id": business_id,
            "client_id": cid,
            "total_amount": total_amount,
        },
    )
    return sid


async def _insert_sale_item(
    db_session: AsyncSession,
    *,
    business_id: str,
    sale_id: str,
    product_id: str,
    quantity: Decimal = Decimal("1.00"),
    unit_price: Decimal = Decimal("100.00"),
    unit_cost: Decimal = Decimal("50.00"),
    item_id: str | None = None,
) -> str:
    iid = item_id or str(uuid.uuid4())
    await db_session.execute(
        text(
            """
            INSERT INTO sale_items (
                id, business_id, sale_id, product_id, quantity, unit_price, unit_cost
            )
            VALUES (
                :id, :business_id, :sale_id, :product_id, :quantity, :unit_price, :unit_cost
            )
            """
        ),
        {
            "id": iid,
            "business_id": business_id,
            "sale_id": sale_id,
            "product_id": product_id,
            "quantity": quantity,
            "unit_price": unit_price,
            "unit_cost": unit_cost,
        },
    )
    return iid


async def _insert_payment(
    db_session: AsyncSession,
    *,
    business_id: str,
    sale_id: str,
    payment_method: str = "cash",
    amount: Decimal = Decimal("100.00"),
    payment_id: str | None = None,
) -> str:
    pay_id = payment_id or str(uuid.uuid4())
    await db_session.execute(
        text(
            """
            INSERT INTO payments (id, business_id, sale_id, payment_method, amount)
            VALUES (:id, :business_id, :sale_id, :payment_method, :amount)
            """
        ),
        {
            "id": pay_id,
            "business_id": business_id,
            "sale_id": sale_id,
            "payment_method": payment_method,
            "amount": amount,
        },
    )
    return pay_id


@pytest.mark.asyncio
async def test_insert_sale_valid_with_defaults(db_session: AsyncSession) -> None:
    business_id = str(uuid.uuid4())
    client_id = str(uuid.uuid4())
    async with db_session.begin() as tx:
        try:
            await _insert_business(db_session, business_id, "Almacen Ventas")

            result = await db_session.execute(
                text(
                    """
                    INSERT INTO sales (business_id, client_id, total_amount)
                    VALUES (:business_id, :client_id, :total_amount)
                    RETURNING id, business_id, client_id, total_amount, created_at
                    """
                ),
                {
                    "business_id": business_id,
                    "client_id": client_id,
                    "total_amount": Decimal("1500.75"),
                },
            )
            row = result.mappings().one()
            assert uuid.UUID(str(row["id"]))
            assert str(row["business_id"]) == business_id
            assert str(row["client_id"]) == client_id
            assert isinstance(row["total_amount"], Decimal)
            assert row["total_amount"] == Decimal("1500.75")
            assert row["created_at"] is not None
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_insert_sale_rejects_nulls_on_mandatory_attributes(
    db_session: AsyncSession,
) -> None:
    business_id = str(uuid.uuid4())
    client_id = str(uuid.uuid4())
    async with db_session.begin() as tx:
        try:
            await _insert_business(db_session, business_id, "Comercio Nulls Sales")

            null_cases = [
                (
                    "INSERT INTO sales (business_id, client_id, total_amount) "
                    "VALUES (NULL, :c_id, 100.00)",
                    {"c_id": client_id},
                ),
                (
                    "INSERT INTO sales (business_id, client_id, total_amount) "
                    "VALUES (:b_id, NULL, 100.00)",
                    {"b_id": business_id},
                ),
                (
                    "INSERT INTO sales (business_id, client_id, total_amount) "
                    "VALUES (:b_id, :c_id, NULL)",
                    {"b_id": business_id, "c_id": client_id},
                ),
                (
                    "INSERT INTO sales (business_id, client_id, total_amount, created_at) "
                    "VALUES (:b_id, :c_id, 100.00, NULL)",
                    {"b_id": business_id, "c_id": client_id},
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
async def test_sales_rejects_zero_or_negative_total_amount(
    db_session: AsyncSession,
) -> None:
    business_id = str(uuid.uuid4())
    async with db_session.begin() as tx:
        try:
            await _insert_business(db_session, business_id, "Comercio Total")
            sid = await _insert_sale(
                db_session, business_id=business_id, total_amount=Decimal("50.00")
            )

            for invalid_total in (Decimal("0.00"), Decimal("-10.00")):
                with pytest.raises(IntegrityError) as exc_ins:
                    async with db_session.begin_nested():
                        await _insert_sale(
                            db_session, business_id=business_id, total_amount=invalid_total
                        )
                _assert_sqlstate(exc_ins.value, "23514")

                with pytest.raises(IntegrityError) as exc_upd:
                    async with db_session.begin_nested():
                        await db_session.execute(
                            text("UPDATE sales SET total_amount = :total WHERE id = :id"),
                            {"total": invalid_total, "id": sid},
                        )
                _assert_sqlstate(exc_upd.value, "23514")
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_sales_duplicate_client_id_within_business_supports_idempotency(
    db_session: AsyncSession,
) -> None:
    business_id = str(uuid.uuid4())
    client_id = str(uuid.uuid4())
    async with db_session.begin() as tx:
        try:
            await _insert_business(db_session, business_id, "Comercio Idempotente")
            original_id = await _insert_sale(
                db_session,
                business_id=business_id,
                client_id=client_id,
                total_amount=Decimal("250.00"),
            )

            with pytest.raises(IntegrityError) as exc_dup:
                async with db_session.begin_nested():
                    await _insert_sale(
                        db_session,
                        business_id=business_id,
                        client_id=client_id,
                        total_amount=Decimal("250.00"),
                    )
            _assert_sqlstate(exc_dup.value, "23505")

            conflict_res = (
                await db_session.execute(
                    text(
                        """
                        INSERT INTO sales (business_id, client_id, total_amount)
                        VALUES (:b_id, :c_id, :total)
                        ON CONFLICT (business_id, client_id) DO NOTHING
                        RETURNING id
                        """
                    ),
                    {"b_id": business_id, "c_id": client_id, "total": Decimal("250.00")},
                )
            ).fetchall()
            assert conflict_res == []

            rows = (
                await db_session.execute(
                    text(
                        """
                        SELECT id
                        FROM sales
                        WHERE business_id = :b_id AND client_id = :c_id
                        """
                    ),
                    {"b_id": business_id, "c_id": client_id},
                )
            ).fetchall()
            assert len(rows) == 1
            assert str(rows[0][0]) == original_id
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_sales_same_client_id_allowed_across_distinct_businesses(
    db_session: AsyncSession,
) -> None:
    b1 = str(uuid.uuid4())
    b2 = str(uuid.uuid4())
    shared_client_id = str(uuid.uuid4())
    async with db_session.begin() as tx:
        try:
            await _insert_business(db_session, b1, "Comercio A")
            await _insert_business(db_session, b2, "Comercio B")

            s1 = await _insert_sale(
                db_session,
                business_id=b1,
                client_id=shared_client_id,
                total_amount=Decimal("100.00"),
            )
            s2 = await _insert_sale(
                db_session,
                business_id=b2,
                client_id=shared_client_id,
                total_amount=Decimal("200.00"),
            )
            assert s1 != s2

            count = (
                await db_session.execute(
                    text("SELECT count(*) FROM sales WHERE client_id = :c_id"),
                    {"c_id": shared_client_id},
                )
            ).scalar_one()
            assert count == 2
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_sales_rejects_orphan_business_and_cascades_on_business_delete(
    db_session: AsyncSession,
) -> None:
    non_existent_business = str(uuid.uuid4())
    with pytest.raises(IntegrityError) as exc_orphan:
        async with db_session.begin():
            await _insert_sale(
                db_session,
                business_id=non_existent_business,
                total_amount=Decimal("50.00"),
            )
    _assert_sqlstate(exc_orphan.value, "23503")

    business_id = str(uuid.uuid4())
    async with db_session.begin() as tx:
        try:
            await _insert_business(db_session, business_id, "Comercio Cascade")
            pid = await _insert_product(db_session, business_id=business_id, name="Prod Cascade")
            s1 = await _insert_sale(
                db_session, business_id=business_id, total_amount=Decimal("10.00")
            )
            await _insert_sale(db_session, business_id=business_id, total_amount=Decimal("20.00"))
            await _insert_sale_item(
                db_session,
                business_id=business_id,
                sale_id=s1,
                product_id=pid,
                quantity=Decimal("1.00"),
                unit_price=Decimal("10.00"),
                unit_cost=Decimal("5.00"),
            )
            await _insert_payment(
                db_session,
                business_id=business_id,
                sale_id=s1,
                payment_method="cash",
                amount=Decimal("10.00"),
            )

            await db_session.execute(
                text("DELETE FROM businesses WHERE id = :id"),
                {"id": business_id},
            )
            for table_name in ("sales", "sale_items", "payments"):
                remaining = (
                    await db_session.execute(
                        text(f"SELECT count(*) FROM {table_name} WHERE business_id = :b_id"),
                        {"b_id": business_id},
                    )
                ).scalar_one()
                assert remaining == 0, f"{table_name} rows should cascade on business delete"
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_sale_item_freezes_unit_price_and_unit_cost_after_product_edit(
    db_session: AsyncSession,
) -> None:
    business_id = str(uuid.uuid4())
    async with db_session.begin() as tx:
        try:
            await _insert_business(db_session, business_id, "Almacen Snapshot")
            pid = await _insert_product(
                db_session,
                business_id=business_id,
                name="Cafe 500g",
                sale_price=Decimal("1500.00"),
                cost_price=Decimal("900.00"),
            )
            sid = await _insert_sale(
                db_session, business_id=business_id, total_amount=Decimal("3000.00")
            )
            item_id = await _insert_sale_item(
                db_session,
                business_id=business_id,
                sale_id=sid,
                product_id=pid,
                quantity=Decimal("2.00"),
                unit_price=Decimal("1500.00"),
                unit_cost=Decimal("900.00"),
            )

            await db_session.execute(
                text(
                    """
                    UPDATE products
                    SET sale_price = 2000.00, cost_price = 1100.00
                    WHERE id = :pid
                    """
                ),
                {"pid": pid},
            )

            frozen = (
                (
                    await db_session.execute(
                        text(
                            """
                            SELECT quantity, unit_price, unit_cost
                            FROM sale_items
                            WHERE id = :item_id
                            """
                        ),
                        {"item_id": item_id},
                    )
                )
                .mappings()
                .one()
            )
            assert frozen["quantity"] == Decimal("2.00")
            assert frozen["unit_price"] == Decimal("1500.00")
            assert frozen["unit_cost"] == Decimal("900.00")
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_sales_exact_decimal_precision_without_float(
    db_session: AsyncSession,
) -> None:
    business_id = str(uuid.uuid4())
    async with db_session.begin() as tx:
        try:
            cols = (
                (
                    await db_session.execute(
                        text(
                            """
                            SELECT table_name, column_name, data_type,
                                   numeric_precision, numeric_scale
                            FROM information_schema.columns
                            WHERE table_schema = 'public'
                              AND (
                                (table_name = 'sales' AND column_name = 'total_amount')
                                OR (table_name = 'sale_items'
                                    AND column_name IN ('quantity', 'unit_price', 'unit_cost'))
                                OR (table_name = 'payments' AND column_name = 'amount')
                              )
                            ORDER BY table_name, column_name
                            """
                        )
                    )
                )
                .mappings()
                .all()
            )

            assert [(c["table_name"], c["column_name"]) for c in cols] == [
                ("payments", "amount"),
                ("sale_items", "quantity"),
                ("sale_items", "unit_cost"),
                ("sale_items", "unit_price"),
                ("sales", "total_amount"),
            ]
            for col in cols:
                assert col["data_type"] == "numeric"
                assert col["numeric_precision"] == 12
                assert col["numeric_scale"] == 2

            await _insert_business(db_session, business_id, "Libreria Decimal")
            pid = await _insert_product(
                db_session,
                business_id=business_id,
                sale_price=Decimal("0.30"),
                cost_price=Decimal("0.20"),
            )
            sid = await _insert_sale(
                db_session, business_id=business_id, total_amount=Decimal("0.30")
            )
            item_id = await _insert_sale_item(
                db_session,
                business_id=business_id,
                sale_id=sid,
                product_id=pid,
                quantity=Decimal("1.50"),
                unit_price=Decimal("0.20"),
                unit_cost=Decimal("0.10"),
            )
            pay1 = await _insert_payment(
                db_session,
                business_id=business_id,
                sale_id=sid,
                payment_method="cash",
                amount=Decimal("0.10"),
            )
            pay2 = await _insert_payment(
                db_session,
                business_id=business_id,
                sale_id=sid,
                payment_method="card",
                amount=Decimal("0.20"),
            )

            sum_payments = (
                await db_session.execute(
                    text("SELECT SUM(amount) FROM payments WHERE id IN (:p1, :p2)"),
                    {"p1": pay1, "p2": pay2},
                )
            ).scalar_one()
            assert isinstance(sum_payments, Decimal)
            assert sum_payments == Decimal("0.30")

            line_cost = (
                await db_session.execute(
                    text("SELECT quantity * unit_cost FROM sale_items WHERE id = :id"),
                    {"id": item_id},
                )
            ).scalar_one()
            assert isinstance(line_cost, Decimal)
            assert line_cost == Decimal("0.1500")
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_sale_items_rejects_nulls_and_invalid_numeric_bounds(
    db_session: AsyncSession,
) -> None:
    business_id = str(uuid.uuid4())
    async with db_session.begin() as tx:
        try:
            await _insert_business(db_session, business_id, "Tienda Item Bounds")
            pid = await _insert_product(db_session, business_id=business_id)
            sid = await _insert_sale(db_session, business_id=business_id)

            zero_cost_id = await _insert_sale_item(
                db_session,
                business_id=business_id,
                sale_id=sid,
                product_id=pid,
                quantity=Decimal("1.00"),
                unit_price=Decimal("10.00"),
                unit_cost=Decimal("0.00"),
            )
            stored_cost = (
                await db_session.execute(
                    text("SELECT unit_cost FROM sale_items WHERE id = :id"),
                    {"id": zero_cost_id},
                )
            ).scalar_one()
            assert stored_cost == Decimal("0.00")

            null_cases = [
                (
                    "INSERT INTO sale_items "
                    "(business_id, sale_id, product_id, quantity, unit_price, unit_cost) "
                    "VALUES (NULL, :s_id, :p_id, 1.00, 10.00, 5.00)",
                    {"s_id": sid, "p_id": pid},
                ),
                (
                    "INSERT INTO sale_items "
                    "(business_id, sale_id, product_id, quantity, unit_price, unit_cost) "
                    "VALUES (:b_id, NULL, :p_id, 1.00, 10.00, 5.00)",
                    {"b_id": business_id, "p_id": pid},
                ),
                (
                    "INSERT INTO sale_items "
                    "(business_id, sale_id, product_id, quantity, unit_price, unit_cost) "
                    "VALUES (:b_id, :s_id, NULL, 1.00, 10.00, 5.00)",
                    {"b_id": business_id, "s_id": sid},
                ),
                (
                    "INSERT INTO sale_items "
                    "(business_id, sale_id, product_id, quantity, unit_price, unit_cost) "
                    "VALUES (:b_id, :s_id, :p_id, NULL, 10.00, 5.00)",
                    {"b_id": business_id, "s_id": sid, "p_id": pid},
                ),
                (
                    "INSERT INTO sale_items "
                    "(business_id, sale_id, product_id, quantity, unit_price, unit_cost) "
                    "VALUES (:b_id, :s_id, :p_id, 1.00, NULL, 5.00)",
                    {"b_id": business_id, "s_id": sid, "p_id": pid},
                ),
                (
                    "INSERT INTO sale_items "
                    "(business_id, sale_id, product_id, quantity, unit_price, unit_cost) "
                    "VALUES (:b_id, :s_id, :p_id, 1.00, 10.00, NULL)",
                    {"b_id": business_id, "s_id": sid, "p_id": pid},
                ),
                (
                    "INSERT INTO sale_items "
                    "(business_id, sale_id, product_id, quantity, unit_price, "
                    "unit_cost, created_at) "
                    "VALUES (:b_id, :s_id, :p_id, 1.00, 10.00, 5.00, NULL)",
                    {"b_id": business_id, "s_id": sid, "p_id": pid},
                ),
            ]
            for sql, params in null_cases:
                with pytest.raises(IntegrityError) as exc_null:
                    async with db_session.begin_nested():
                        await db_session.execute(text(sql), params)
                _assert_sqlstate(exc_null.value, "23502")

            bad_numeric_cases = [
                (
                    "INSERT INTO sale_items "
                    "(business_id, sale_id, product_id, quantity, unit_price, unit_cost) "
                    "VALUES (:b_id, :s_id, :p_id, :val, 10.00, 5.00)",
                    "UPDATE sale_items SET quantity = :val WHERE id = :item_id",
                    (Decimal("0.00"), Decimal("-1.00")),
                ),
                (
                    "INSERT INTO sale_items "
                    "(business_id, sale_id, product_id, quantity, unit_price, unit_cost) "
                    "VALUES (:b_id, :s_id, :p_id, 1.00, :val, 5.00)",
                    "UPDATE sale_items SET unit_price = :val WHERE id = :item_id",
                    (Decimal("0.00"), Decimal("-5.00")),
                ),
                (
                    "INSERT INTO sale_items "
                    "(business_id, sale_id, product_id, quantity, unit_price, unit_cost) "
                    "VALUES (:b_id, :s_id, :p_id, 1.00, 10.00, :val)",
                    "UPDATE sale_items SET unit_cost = :val WHERE id = :item_id",
                    (Decimal("-0.01"),),
                ),
            ]
            for ins_sql, upd_sql, values in bad_numeric_cases:
                for val in values:
                    with pytest.raises(IntegrityError) as exc_ins:
                        async with db_session.begin_nested():
                            await db_session.execute(
                                text(ins_sql),
                                {"b_id": business_id, "s_id": sid, "p_id": pid, "val": val},
                            )
                    _assert_sqlstate(exc_ins.value, "23514")

                    with pytest.raises(IntegrityError) as exc_upd:
                        async with db_session.begin_nested():
                            await db_session.execute(
                                text(upd_sql),
                                {"val": val, "item_id": zero_cost_id},
                            )
                    _assert_sqlstate(exc_upd.value, "23514")
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_sale_items_composite_fks_reject_cross_business_references(
    db_session: AsyncSession,
) -> None:
    b1 = str(uuid.uuid4())
    b2 = str(uuid.uuid4())
    async with db_session.begin() as tx:
        try:
            await _insert_business(db_session, b1, "Tenant A")
            await _insert_business(db_session, b2, "Tenant B")
            p1 = await _insert_product(db_session, business_id=b1, name="Prod A")
            p2 = await _insert_product(db_session, business_id=b2, name="Prod B")
            s1 = await _insert_sale(db_session, business_id=b1)
            s2 = await _insert_sale(db_session, business_id=b2)

            with pytest.raises(IntegrityError) as exc_cross_sale:
                async with db_session.begin_nested():
                    await _insert_sale_item(
                        db_session,
                        business_id=b2,
                        sale_id=s1,
                        product_id=p2,
                    )
            _assert_sqlstate(exc_cross_sale.value, "23503")

            with pytest.raises(IntegrityError) as exc_cross_product:
                async with db_session.begin_nested():
                    await _insert_sale_item(
                        db_session,
                        business_id=b2,
                        sale_id=s2,
                        product_id=p1,
                    )
            _assert_sqlstate(exc_cross_product.value, "23503")
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_sale_items_restricts_product_delete_and_cascades_on_sale_delete(
    db_session: AsyncSession,
) -> None:
    business_id = str(uuid.uuid4())
    async with db_session.begin() as tx:
        try:
            await _insert_business(db_session, business_id, "Comercio Restrict")
            pid = await _insert_product(db_session, business_id=business_id, name="Prod Historico")
            sid = await _insert_sale(db_session, business_id=business_id)
            await _insert_sale_item(
                db_session,
                business_id=business_id,
                sale_id=sid,
                product_id=pid,
            )

            with pytest.raises(IntegrityError) as exc_restrict:
                async with db_session.begin_nested():
                    await db_session.execute(
                        text("DELETE FROM products WHERE id = :pid"),
                        {"pid": pid},
                    )
            _assert_sqlstate(exc_restrict.value, "23503")

            await db_session.execute(
                text("DELETE FROM sales WHERE id = :sid"),
                {"sid": sid},
            )
            remaining_items = (
                await db_session.execute(
                    text("SELECT count(*) FROM sale_items WHERE sale_id = :sid"),
                    {"sid": sid},
                )
            ).scalar_one()
            assert remaining_items == 0
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_payments_multiple_valid_methods_persisted_for_sale(
    db_session: AsyncSession,
) -> None:
    business_id = str(uuid.uuid4())
    async with db_session.begin() as tx:
        try:
            await _insert_business(db_session, business_id, "Comercio Pagos")
            sid = await _insert_sale(
                db_session, business_id=business_id, total_amount=Decimal("600.00")
            )

            await _insert_payment(
                db_session,
                business_id=business_id,
                sale_id=sid,
                payment_method="cash",
                amount=Decimal("100.00"),
            )
            await _insert_payment(
                db_session,
                business_id=business_id,
                sale_id=sid,
                payment_method="card",
                amount=Decimal("200.00"),
            )
            await _insert_payment(
                db_session,
                business_id=business_id,
                sale_id=sid,
                payment_method="transfer",
                amount=Decimal("300.00"),
            )

            rows = (
                (
                    await db_session.execute(
                        text(
                            """
                            SELECT payment_method, amount
                            FROM payments
                            WHERE sale_id = :sid
                            ORDER BY payment_method
                            """
                        ),
                        {"sid": sid},
                    )
                )
                .mappings()
                .all()
            )
            assert [(r["payment_method"], r["amount"]) for r in rows] == [
                ("card", Decimal("200.00")),
                ("cash", Decimal("100.00")),
                ("transfer", Decimal("300.00")),
            ]
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_payments_rejects_invalid_method_non_positive_amount_and_nulls(
    db_session: AsyncSession,
) -> None:
    business_id = str(uuid.uuid4())
    async with db_session.begin() as tx:
        try:
            await _insert_business(db_session, business_id, "Comercio Validaciones Pago")
            sid = await _insert_sale(db_session, business_id=business_id)
            pay_id = await _insert_payment(
                db_session,
                business_id=business_id,
                sale_id=sid,
                payment_method="cash",
                amount=Decimal("50.00"),
            )

            for bad_method in ("other", "crypto", "", "CASH"):
                with pytest.raises(IntegrityError) as exc_ins_m:
                    async with db_session.begin_nested():
                        await _insert_payment(
                            db_session,
                            business_id=business_id,
                            sale_id=sid,
                            payment_method=bad_method,
                            amount=Decimal("10.00"),
                        )
                _assert_sqlstate(exc_ins_m.value, "23514")

                with pytest.raises(IntegrityError) as exc_upd_m:
                    async with db_session.begin_nested():
                        await db_session.execute(
                            text("UPDATE payments SET payment_method = :m WHERE id = :id"),
                            {"m": bad_method, "id": pay_id},
                        )
                _assert_sqlstate(exc_upd_m.value, "23514")

            for bad_amount in (Decimal("0.00"), Decimal("-1.00")):
                with pytest.raises(IntegrityError) as exc_ins_a:
                    async with db_session.begin_nested():
                        await _insert_payment(
                            db_session,
                            business_id=business_id,
                            sale_id=sid,
                            payment_method="cash",
                            amount=bad_amount,
                        )
                _assert_sqlstate(exc_ins_a.value, "23514")

                with pytest.raises(IntegrityError) as exc_upd_a:
                    async with db_session.begin_nested():
                        await db_session.execute(
                            text("UPDATE payments SET amount = :a WHERE id = :id"),
                            {"a": bad_amount, "id": pay_id},
                        )
                _assert_sqlstate(exc_upd_a.value, "23514")

            null_cases = [
                (
                    "INSERT INTO payments (business_id, sale_id, payment_method, amount) "
                    "VALUES (NULL, :s_id, 'cash', 10.00)",
                    {"s_id": sid},
                ),
                (
                    "INSERT INTO payments (business_id, sale_id, payment_method, amount) "
                    "VALUES (:b_id, NULL, 'cash', 10.00)",
                    {"b_id": business_id},
                ),
                (
                    "INSERT INTO payments (business_id, sale_id, payment_method, amount) "
                    "VALUES (:b_id, :s_id, NULL, 10.00)",
                    {"b_id": business_id, "s_id": sid},
                ),
                (
                    "INSERT INTO payments (business_id, sale_id, payment_method, amount) "
                    "VALUES (:b_id, :s_id, 'cash', NULL)",
                    {"b_id": business_id, "s_id": sid},
                ),
                (
                    "INSERT INTO payments "
                    "(business_id, sale_id, payment_method, amount, created_at) "
                    "VALUES (:b_id, :s_id, 'cash', 10.00, NULL)",
                    {"b_id": business_id, "s_id": sid},
                ),
            ]
            for sql, params in null_cases:
                with pytest.raises(IntegrityError) as exc_null:
                    async with db_session.begin_nested():
                        await db_session.execute(text(sql), params)
                _assert_sqlstate(exc_null.value, "23502")
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_payments_rejects_cross_business_sale_and_cascades_on_sale_delete(
    db_session: AsyncSession,
) -> None:
    b1 = str(uuid.uuid4())
    b2 = str(uuid.uuid4())
    async with db_session.begin() as tx:
        try:
            await _insert_business(db_session, b1, "Tenant A")
            await _insert_business(db_session, b2, "Tenant B")
            s1 = await _insert_sale(db_session, business_id=b1)

            with pytest.raises(IntegrityError) as exc_cross:
                async with db_session.begin_nested():
                    await _insert_payment(
                        db_session,
                        business_id=b2,
                        sale_id=s1,
                        payment_method="cash",
                        amount=Decimal("50.00"),
                    )
            _assert_sqlstate(exc_cross.value, "23503")

            await _insert_payment(
                db_session,
                business_id=b1,
                sale_id=s1,
                payment_method="card",
                amount=Decimal("100.00"),
            )
            await db_session.execute(text("DELETE FROM sales WHERE id = :s1"), {"s1": s1})
            remaining = (
                await db_session.execute(
                    text("SELECT count(*) FROM payments WHERE sale_id = :s1"),
                    {"s1": s1},
                )
            ).scalar_one()
            assert remaining == 0
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_rls_authorized_tenant_dml_and_idempotent_retry_under_app_runtime(
    db_session: AsyncSession,
) -> None:
    b1 = str(uuid.uuid4())
    client_id = str(uuid.uuid4())
    async with db_session.begin() as tx:
        try:
            await _insert_business(db_session, b1, "Tenant Autorizado")
            p1 = await _insert_product(
                db_session, business_id=b1, name="Yerba", sale_price=Decimal("500.00")
            )

            await db_session.execute(text("SET LOCAL ROLE app_runtime;"))
            await db_session.execute(text(f"SET LOCAL app.current_business_id = '{b1}';"))

            inserted = (
                await db_session.execute(
                    text(
                        """
                        INSERT INTO sales (business_id, client_id, total_amount)
                        VALUES (:b_id, :c_id, 500.00)
                        ON CONFLICT (business_id, client_id) DO NOTHING
                        RETURNING id
                        """
                    ),
                    {"b_id": b1, "c_id": client_id},
                )
            ).scalar_one()
            sale_id = str(inserted)

            retry = (
                await db_session.execute(
                    text(
                        """
                        INSERT INTO sales (business_id, client_id, total_amount)
                        VALUES (:b_id, :c_id, 500.00)
                        ON CONFLICT (business_id, client_id) DO NOTHING
                        RETURNING id
                        """
                    ),
                    {"b_id": b1, "c_id": client_id},
                )
            ).fetchall()
            assert retry == []

            item_id = await _insert_sale_item(
                db_session,
                business_id=b1,
                sale_id=sale_id,
                product_id=p1,
                quantity=Decimal("1.00"),
                unit_price=Decimal("500.00"),
                unit_cost=Decimal("300.00"),
            )
            pay_id = await _insert_payment(
                db_session,
                business_id=b1,
                sale_id=sale_id,
                payment_method="cash",
                amount=Decimal("500.00"),
            )

            assert (await db_session.execute(text("SELECT count(*) FROM sales;"))).scalar_one() == 1
            assert (
                await db_session.execute(text("SELECT count(*) FROM sale_items;"))
            ).scalar_one() == 1
            assert (
                await db_session.execute(text("SELECT count(*) FROM payments;"))
            ).scalar_one() == 1

            await db_session.execute(
                text("UPDATE sales SET total_amount = 550.00 WHERE id = :id"),
                {"id": sale_id},
            )
            await db_session.execute(
                text("UPDATE sale_items SET quantity = 2.00 WHERE id = :id"),
                {"id": item_id},
            )
            await db_session.execute(
                text("UPDATE payments SET amount = 550.00 WHERE id = :id"),
                {"id": pay_id},
            )

            del_pay = await db_session.execute(
                text("DELETE FROM payments WHERE id = :id"), {"id": pay_id}
            )
            del_item = await db_session.execute(
                text("DELETE FROM sale_items WHERE id = :id"), {"id": item_id}
            )
            del_sale = await db_session.execute(
                text("DELETE FROM sales WHERE id = :id"), {"id": sale_id}
            )
            assert del_pay.rowcount == 1
            assert del_item.rowcount == 1
            assert del_sale.rowcount == 1
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_rls_cross_tenant_select_update_delete_blocked_across_sales_tables(
    db_session: AsyncSession,
) -> None:
    b1 = str(uuid.uuid4())
    b2 = str(uuid.uuid4())
    async with db_session.begin() as tx:
        try:
            await _insert_business(db_session, b1, "Tenant A")
            await _insert_business(db_session, b2, "Tenant B")
            p1 = await _insert_product(db_session, business_id=b1, name="Prod A")
            p2 = await _insert_product(db_session, business_id=b2, name="Prod B")

            s1 = await _insert_sale(db_session, business_id=b1, total_amount=Decimal("100.00"))
            s2 = await _insert_sale(db_session, business_id=b2, total_amount=Decimal("200.00"))
            i1 = await _insert_sale_item(db_session, business_id=b1, sale_id=s1, product_id=p1)
            i2 = await _insert_sale_item(db_session, business_id=b2, sale_id=s2, product_id=p2)
            pay1 = await _insert_payment(db_session, business_id=b1, sale_id=s1)
            pay2 = await _insert_payment(db_session, business_id=b2, sale_id=s2)

            await db_session.execute(text("SET LOCAL ROLE app_runtime;"))
            await db_session.execute(text(f"SET LOCAL app.current_business_id = '{b1}';"))

            assert [
                str(r[0])
                for r in (await db_session.execute(text("SELECT id FROM sales;"))).fetchall()
            ] == [s1]
            assert [
                str(r[0])
                for r in (await db_session.execute(text("SELECT id FROM sale_items;"))).fetchall()
            ] == [i1]
            assert [
                str(r[0])
                for r in (await db_session.execute(text("SELECT id FROM payments;"))).fetchall()
            ] == [pay1]

            assert (
                await db_session.execute(
                    text("SELECT id FROM sales WHERE business_id = :b2;"), {"b2": b2}
                )
            ).fetchall() == []
            assert (
                await db_session.execute(
                    text("SELECT id FROM sale_items WHERE business_id = :b2;"), {"b2": b2}
                )
            ).fetchall() == []
            assert (
                await db_session.execute(
                    text("SELECT id FROM payments WHERE business_id = :b2;"), {"b2": b2}
                )
            ).fetchall() == []

            assert (
                await db_session.execute(
                    text("UPDATE sales SET total_amount = 999.00 WHERE id = :s2;"), {"s2": s2}
                )
            ).rowcount == 0
            assert (
                await db_session.execute(
                    text("UPDATE sale_items SET quantity = 99.00 WHERE id = :i2;"), {"i2": i2}
                )
            ).rowcount == 0
            assert (
                await db_session.execute(
                    text("UPDATE payments SET amount = 999.00 WHERE id = :pay2;"), {"pay2": pay2}
                )
            ).rowcount == 0

            assert (
                await db_session.execute(
                    text("DELETE FROM payments WHERE id = :pay2;"), {"pay2": pay2}
                )
            ).rowcount == 0
            assert (
                await db_session.execute(text("DELETE FROM sale_items WHERE id = :i2;"), {"i2": i2})
            ).rowcount == 0
            assert (
                await db_session.execute(text("DELETE FROM sales WHERE id = :s2;"), {"s2": s2})
            ).rowcount == 0

            # Unfiltered DELETE must only affect tenant A, leaving tenant B intact
            assert (await db_session.execute(text("DELETE FROM payments;"))).rowcount == 1
            assert (await db_session.execute(text("DELETE FROM sale_items;"))).rowcount == 1
            assert (await db_session.execute(text("DELETE FROM sales;"))).rowcount == 1

            await db_session.execute(text("RESET ROLE;"))
            assert (
                await db_session.execute(
                    text("SELECT total_amount FROM sales WHERE id = :s2;"), {"s2": s2}
                )
            ).scalar_one() == Decimal("200.00")
            assert (
                await db_session.execute(
                    text("SELECT count(*) FROM sale_items WHERE id = :i2;"), {"i2": i2}
                )
            ).scalar_one() == 1
            assert (
                await db_session.execute(
                    text("SELECT count(*) FROM payments WHERE id = :pay2;"), {"pay2": pay2}
                )
            ).scalar_one() == 1
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_rls_cross_tenant_insert_and_update_hijack_rejected(
    db_session: AsyncSession,
) -> None:
    b1 = str(uuid.uuid4())
    b2 = str(uuid.uuid4())
    async with db_session.begin() as tx:
        try:
            await _insert_business(db_session, b1, "Tenant A")
            await _insert_business(db_session, b2, "Tenant B")
            p1 = await _insert_product(db_session, business_id=b1, name="Prod A")
            p2 = await _insert_product(db_session, business_id=b2, name="Prod B")
            s1 = await _insert_sale(db_session, business_id=b1)
            s2 = await _insert_sale(db_session, business_id=b2)
            i1 = await _insert_sale_item(db_session, business_id=b1, sale_id=s1, product_id=p1)
            pay1 = await _insert_payment(db_session, business_id=b1, sale_id=s1)

            await db_session.execute(text("SET LOCAL ROLE app_runtime;"))
            await db_session.execute(text(f"SET LOCAL app.current_business_id = '{b1}';"))

            cross_inserts = [
                (
                    "INSERT INTO sales (business_id, client_id, total_amount) "
                    "VALUES (:b2, :c_id, 100.00);",
                    {"b2": b2, "c_id": str(uuid.uuid4())},
                ),
                (
                    "INSERT INTO sales (business_id, client_id, total_amount) "
                    "VALUES (:b2, :c_id, 100.00) ON CONFLICT (business_id, client_id) DO NOTHING;",
                    {"b2": b2, "c_id": str(uuid.uuid4())},
                ),
                (
                    "INSERT INTO sale_items "
                    "(business_id, sale_id, product_id, quantity, unit_price, unit_cost) "
                    "VALUES (:b2, :s2, :p2, 1.00, 100.00, 50.00);",
                    {"b2": b2, "s2": s2, "p2": p2},
                ),
                (
                    "INSERT INTO payments (business_id, sale_id, payment_method, amount) "
                    "VALUES (:b2, :s2, 'cash', 100.00);",
                    {"b2": b2, "s2": s2},
                ),
            ]
            for sql, params in cross_inserts:
                with pytest.raises(DBAPIError) as exc_ins:
                    async with db_session.begin_nested():
                        await db_session.execute(text(sql), params)
                _assert_sqlstate(exc_ins.value, "42501")

            cross_updates = [
                ("UPDATE sales SET business_id = :b2 WHERE id = :s1;", {"b2": b2, "s1": s1}),
                ("UPDATE sales SET business_id = :b2;", {"b2": b2}),
                ("UPDATE sale_items SET business_id = :b2 WHERE id = :i1;", {"b2": b2, "i1": i1}),
                ("UPDATE sale_items SET business_id = :b2;", {"b2": b2}),
                (
                    "UPDATE payments SET business_id = :b2 WHERE id = :pay1;",
                    {"b2": b2, "pay1": pay1},
                ),
                ("UPDATE payments SET business_id = :b2;", {"b2": b2}),
            ]
            for sql, params in cross_updates:
                with pytest.raises(DBAPIError) as exc_upd:
                    async with db_session.begin_nested():
                        await db_session.execute(text(sql), params)
                _assert_sqlstate(exc_upd.value, "42501")
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_rls_without_tenant_context_returns_empty_and_blocks_writes(
    db_session: AsyncSession,
) -> None:
    b1 = str(uuid.uuid4())
    async with db_session.begin() as tx:
        try:
            await _insert_business(db_session, b1, "Tenant Con Datos")
            p1 = await _insert_product(db_session, business_id=b1, name="Prod")
            s1 = await _insert_sale(db_session, business_id=b1)
            await _insert_sale_item(db_session, business_id=b1, sale_id=s1, product_id=p1)
            await _insert_payment(db_session, business_id=b1, sale_id=s1)

            await db_session.execute(text("SET LOCAL ROLE app_runtime;"))

            for ctx_sql in (None, "SET LOCAL app.current_business_id = '';"):
                if ctx_sql is not None:
                    await db_session.execute(text(ctx_sql))

                for table_name in ("sales", "sale_items", "payments"):
                    assert (
                        await db_session.execute(text(f"SELECT id FROM {table_name};"))
                    ).fetchall() == []
                    assert (
                        await db_session.execute(text(f"DELETE FROM {table_name};"))
                    ).rowcount == 0

                assert (
                    await db_session.execute(text("UPDATE sales SET total_amount = 1.00;"))
                ).rowcount == 0
                assert (
                    await db_session.execute(text("UPDATE sale_items SET quantity = 1.00;"))
                ).rowcount == 0
                assert (
                    await db_session.execute(text("UPDATE payments SET amount = 1.00;"))
                ).rowcount == 0

                blocked_inserts = [
                    (
                        "INSERT INTO sales (business_id, client_id, total_amount) "
                        "VALUES (:b_id, :c_id, 10.00);",
                        {"b_id": b1, "c_id": str(uuid.uuid4())},
                    ),
                    (
                        "INSERT INTO sale_items "
                        "(business_id, sale_id, product_id, quantity, unit_price, unit_cost) "
                        "VALUES (:b_id, :s_id, :p_id, 1.00, 10.00, 5.00);",
                        {"b_id": b1, "s_id": s1, "p_id": p1},
                    ),
                    (
                        "INSERT INTO payments (business_id, sale_id, payment_method, amount) "
                        "VALUES (:b_id, :s_id, 'cash', 10.00);",
                        {"b_id": b1, "s_id": s1},
                    ),
                ]
                for sql, params in blocked_inserts:
                    with pytest.raises(DBAPIError) as exc_ins:
                        async with db_session.begin_nested():
                            await db_session.execute(text(sql), params)
                    _assert_sqlstate(exc_ins.value, "42501")
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_sales_metadata_forced_rls_non_privileged_ownership_and_grants(
    db_session: AsyncSession,
) -> None:
    async with db_session.begin() as tx:
        try:
            for table_name in ("sales", "sale_items", "payments"):
                rls_row = (
                    await db_session.execute(
                        text(
                            """
                            SELECT c.relrowsecurity, c.relforcerowsecurity
                            FROM pg_class c
                            JOIN pg_namespace n ON n.oid = c.relnamespace
                            WHERE n.nspname = 'public' AND c.relname = :tbl;
                            """
                        ),
                        {"tbl": table_name},
                    )
                ).one_or_none()
                assert rls_row is not None, f"Table public.{table_name} must exist"
                assert rls_row[0] is True, f"{table_name} must have ENABLE ROW LEVEL SECURITY"
                assert rls_row[1] is True, f"{table_name} must have FORCE ROW LEVEL SECURITY"

                owner = (
                    await db_session.execute(
                        text(
                            """
                            SELECT tableowner
                            FROM pg_tables
                            WHERE schemaname = 'public' AND tablename = :tbl;
                            """
                        ),
                        {"tbl": table_name},
                    )
                ).scalar_one()
                assert owner not in ("app_api", "app_runtime")

                grants = {
                    row[0]
                    for row in (
                        await db_session.execute(
                            text(
                                """
                                SELECT privilege_type
                                FROM information_schema.role_table_grants
                                WHERE table_schema = 'public'
                                  AND table_name = :tbl
                                  AND grantee = 'app_api';
                                """
                            ),
                            {"tbl": table_name},
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
                              AND table_name = :tbl
                              AND grantee IN ('PUBLIC', 'anon', 'authenticated');
                            """
                        ),
                        {"tbl": table_name},
                    )
                ).fetchall()
                assert public_grants == []

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
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_app_runtime_cannot_truncate_sales_tables(
    db_session: AsyncSession,
) -> None:
    b1 = str(uuid.uuid4())
    async with db_session.begin() as tx:
        try:
            await _insert_business(db_session, b1, "Tenant Truncate")
            p1 = await _insert_product(db_session, business_id=b1, name="No Truncar")
            s1 = await _insert_sale(db_session, business_id=b1)
            await _insert_sale_item(db_session, business_id=b1, sale_id=s1, product_id=p1)
            await _insert_payment(db_session, business_id=b1, sale_id=s1)

            await db_session.execute(text("SET LOCAL ROLE app_runtime;"))
            await db_session.execute(text(f"SET LOCAL app.current_business_id = '{b1}';"))

            for table_name in ("payments", "sale_items", "sales"):
                with pytest.raises(DBAPIError) as exc_trunc:
                    async with db_session.begin_nested():
                        await db_session.execute(text(f"TRUNCATE {table_name};"))
                _assert_sqlstate(exc_trunc.value, "42501")
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_authenticated_and_anon_cannot_access_or_truncate_sales_tables(
    db_session: AsyncSession,
) -> None:
    b1 = str(uuid.uuid4())
    async with db_session.begin() as tx:
        try:
            await _insert_business(db_session, b1, "Negocio Privado")
            p1 = await _insert_product(db_session, business_id=b1, name="Secreto")
            s1 = await _insert_sale(db_session, business_id=b1)
            i1 = await _insert_sale_item(db_session, business_id=b1, sale_id=s1, product_id=p1)
            pay1 = await _insert_payment(db_session, business_id=b1, sale_id=s1)

            for role in ("authenticated", "anon"):
                await db_session.execute(text(f"SET LOCAL ROLE {role};"))

                statements = [
                    ("SELECT id FROM sales LIMIT 1;", {}),
                    (
                        "INSERT INTO sales (business_id, client_id, total_amount) "
                        "VALUES (:b_id, :c_id, 1.00);",
                        {"b_id": b1, "c_id": str(uuid.uuid4())},
                    ),
                    ("UPDATE sales SET total_amount = 1.00 WHERE id = :s1;", {"s1": s1}),
                    ("DELETE FROM sales WHERE id = :s1;", {"s1": s1}),
                    ("TRUNCATE sales;", {}),
                    ("SELECT id FROM sale_items LIMIT 1;", {}),
                    (
                        "INSERT INTO sale_items "
                        "(business_id, sale_id, product_id, quantity, unit_price, unit_cost) "
                        "VALUES (:b_id, :s1, :p1, 1.00, 1.00, 0.00);",
                        {"b_id": b1, "s1": s1, "p1": p1},
                    ),
                    ("UPDATE sale_items SET quantity = 1.00 WHERE id = :i1;", {"i1": i1}),
                    ("DELETE FROM sale_items WHERE id = :i1;", {"i1": i1}),
                    ("TRUNCATE sale_items;", {}),
                    ("SELECT id FROM payments LIMIT 1;", {}),
                    (
                        "INSERT INTO payments (business_id, sale_id, payment_method, amount) "
                        "VALUES (:b_id, :s1, 'cash', 1.00);",
                        {"b_id": b1, "s1": s1},
                    ),
                    ("UPDATE payments SET amount = 1.00 WHERE id = :pay1;", {"pay1": pay1}),
                    ("DELETE FROM payments WHERE id = :pay1;", {"pay1": pay1}),
                    ("TRUNCATE payments;", {}),
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
async def test_sales_tables_reject_duplicate_primary_keys(
    db_session: AsyncSession,
) -> None:
    business_id = str(uuid.uuid4())
    other_business_id = str(uuid.uuid4())
    sale_id = str(uuid.uuid4())
    item_id = str(uuid.uuid4())
    payment_id = str(uuid.uuid4())
    async with db_session.begin() as tx:
        try:
            await _insert_business(db_session, business_id, "Comercio PKs")
            await _insert_business(db_session, other_business_id, "Comercio PKs 2")
            pid = await _insert_product(db_session, business_id=business_id, name="Prod PK")
            await _insert_sale(
                db_session,
                business_id=business_id,
                client_id=str(uuid.uuid4()),
                sale_id=sale_id,
            )
            await _insert_sale_item(
                db_session,
                business_id=business_id,
                sale_id=sale_id,
                product_id=pid,
                item_id=item_id,
            )
            await _insert_payment(
                db_session,
                business_id=business_id,
                sale_id=sale_id,
                payment_id=payment_id,
            )

            with pytest.raises(IntegrityError) as exc_sale_pk:
                async with db_session.begin_nested():
                    await _insert_sale(
                        db_session,
                        business_id=other_business_id,
                        client_id=str(uuid.uuid4()),
                        sale_id=sale_id,
                    )
            _assert_sqlstate(exc_sale_pk.value, "23505")

            with pytest.raises(IntegrityError) as exc_item_pk:
                async with db_session.begin_nested():
                    await _insert_sale_item(
                        db_session,
                        business_id=business_id,
                        sale_id=sale_id,
                        product_id=pid,
                        item_id=item_id,
                    )
            _assert_sqlstate(exc_item_pk.value, "23505")

            with pytest.raises(IntegrityError) as exc_payment_pk:
                async with db_session.begin_nested():
                    await _insert_payment(
                        db_session,
                        business_id=business_id,
                        sale_id=sale_id,
                        payment_id=payment_id,
                    )
            _assert_sqlstate(exc_payment_pk.value, "23505")
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_sale_items_and_payments_valid_with_defaults(
    db_session: AsyncSession,
) -> None:
    business_id = str(uuid.uuid4())
    async with db_session.begin() as tx:
        try:
            await _insert_business(db_session, business_id, "Comercio Defaults")
            pid = await _insert_product(db_session, business_id=business_id, name="Prod Defaults")
            sid = await _insert_sale(db_session, business_id=business_id)

            item_row = (
                (
                    await db_session.execute(
                        text(
                            """
                            INSERT INTO sale_items (
                                business_id, sale_id, product_id, quantity, unit_price, unit_cost
                            )
                            VALUES (
                                :business_id, :sale_id, :product_id, 2.00, 50.00, 25.00
                            )
                            RETURNING id, created_at
                            """
                        ),
                        {"business_id": business_id, "sale_id": sid, "product_id": pid},
                    )
                )
                .mappings()
                .one()
            )
            assert uuid.UUID(str(item_row["id"]))
            assert item_row["created_at"] is not None

            payment_row = (
                (
                    await db_session.execute(
                        text(
                            """
                            INSERT INTO payments (business_id, sale_id, payment_method, amount)
                            VALUES (:business_id, :sale_id, 'cash', 100.00)
                            RETURNING id, created_at
                            """
                        ),
                        {"business_id": business_id, "sale_id": sid},
                    )
                )
                .mappings()
                .one()
            )
            assert uuid.UUID(str(payment_row["id"]))
            assert payment_row["created_at"] is not None
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_sales_tables_explicit_btree_indexes_exist_with_expected_columns(
    db_session: AsyncSession,
) -> None:
    expected_indexes = {
        "ix_sales_business_id_created_at": ("sales", "btree", ["business_id", "created_at"]),
        "ix_sale_items_business_id_sale_id": ("sale_items", "btree", ["business_id", "sale_id"]),
        "ix_sale_items_business_id_product_id": (
            "sale_items",
            "btree",
            ["business_id", "product_id"],
        ),
        "ix_payments_business_id_sale_id": ("payments", "btree", ["business_id", "sale_id"]),
    }
    async with db_session.begin() as tx:
        try:
            rows = (
                (
                    await db_session.execute(
                        text(
                            """
                            SELECT
                                i.relname AS index_name,
                                t.relname AS table_name,
                                am.amname AS access_method,
                                array_agg(a.attname::text ORDER BY u.ord) AS columns
                            FROM pg_index ix
                            JOIN pg_class t ON t.oid = ix.indrelid
                            JOIN pg_namespace n ON n.oid = t.relnamespace
                            JOIN pg_class i ON i.oid = ix.indexrelid
                            JOIN pg_am am ON am.oid = i.relam
                            CROSS JOIN LATERAL unnest(ix.indkey) WITH ORDINALITY AS u(attnum, ord)
                            JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = u.attnum
                            WHERE n.nspname = 'public'
                              AND i.relname = ANY(:index_names)
                            GROUP BY i.relname, t.relname, am.amname
                            """
                        ),
                        {"index_names": list(expected_indexes.keys())},
                    )
                )
                .mappings()
                .all()
            )
            actual = {
                row["index_name"]: (
                    row["table_name"],
                    row["access_method"],
                    list(row["columns"]),
                )
                for row in rows
            }
            assert actual == expected_indexes
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_sales_tables_business_fk_cascade_metadata(
    db_session: AsyncSession,
) -> None:
    expected_fks = {
        "fk_sale_items_business_id": ("sale_items", "businesses", "c"),
        "fk_payments_business_id": ("payments", "businesses", "c"),
    }
    async with db_session.begin() as tx:
        try:
            rows = (
                (
                    await db_session.execute(
                        text(
                            """
                            SELECT
                                con.conname AS constraint_name,
                                rel.relname AS table_name,
                                frel.relname AS referenced_table,
                                con.confdeltype::text AS delete_action
                            FROM pg_constraint con
                            JOIN pg_class rel ON rel.oid = con.conrelid
                            JOIN pg_namespace n ON n.oid = rel.relnamespace
                            JOIN pg_class frel ON frel.oid = con.confrelid
                            WHERE n.nspname = 'public'
                              AND con.contype = 'f'
                              AND con.conname = ANY(:fk_names)
                            """
                        ),
                        {"fk_names": list(expected_fks.keys())},
                    )
                )
                .mappings()
                .all()
            )
            actual = {
                row["constraint_name"]: (
                    row["table_name"],
                    row["referenced_table"],
                    row["delete_action"],
                )
                for row in rows
            }
            assert actual == expected_fks
        finally:
            await tx.rollback()
