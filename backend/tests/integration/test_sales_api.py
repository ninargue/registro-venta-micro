import asyncio
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
import jwt
import pytest
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.main import app
from app.scripts.export_openapi import check_openapi

TEST_JWT_SECRET = "test-jwt-secret-key-for-sales-tests-32b"
SALES_URL = "/api/v1/sales"


@pytest.fixture
def sales_auth_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("JWT_SECRET_KEY", TEST_JWT_SECRET)
    monkeypatch.setenv("COOKIE_SECURE", "false")
    if hasattr(get_settings, "cache_clear"):
        get_settings.cache_clear()
    yield
    if hasattr(get_settings, "cache_clear"):
        get_settings.cache_clear()


def _make_jwt_cookie(
    user_id: str,
    email: str = "owner@example.com",
    business_id: str | None = None,
    role: str | None = None,
    exp_offset_seconds: int = 900,
) -> dict[str, str]:
    now = int(time.time())
    payload: dict[str, Any] = {
        "sub": user_id,
        "email": email,
        "business_id": business_id,
        "role": role,
        "token_type": "access",
        "iat": now,
        "exp": now + exp_offset_seconds,
    }
    token = jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")
    return {"access_token": token}


async def _seed_business(
    db_session: AsyncSession,
    business_id: str,
    name: str = "Kiosco Ventas",
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


async def _seed_business_user(
    db_session: AsyncSession,
    business_id: str,
    user_id: str,
    role: str = "owner",
) -> None:
    await db_session.execute(
        text(
            """
            INSERT INTO business_users (business_id, user_id, role)
            VALUES (:b_id, :u_id, :role)
            """
        ),
        {"b_id": business_id, "u_id": user_id, "role": role},
    )


async def _seed_product(
    db_session: AsyncSession,
    *,
    business_id: str,
    name: str,
    sale_price: Decimal = Decimal("100.00"),
    cost_price: Decimal = Decimal("50.00"),
    stock: Decimal = Decimal("10.00"),
    code: str | None = None,
    is_active: bool = True,
    product_id: str | None = None,
) -> str:
    pid = product_id or str(uuid.uuid4())
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


async def _cleanup_businesses(db_session: AsyncSession, business_ids: list[str]) -> None:
    if not business_ids:
        return
    async with db_session.begin():
        for b_id in business_ids:
            await db_session.execute(
                text("DELETE FROM businesses WHERE id = :id"),
                {"id": b_id},
            )


@contextmanager
def _capture_sql_statements() -> Iterator[list[tuple[str, str]]]:
    statements: list[tuple[str, str]] = []

    def _listener(
        conn: Any,
        cursor: Any,
        statement: str,
        parameters: Any,
        context: Any,
        executemany: bool,
    ) -> None:
        statements.append((statement.lower(), repr(parameters)))

    event.listen(Engine, "before_cursor_execute", _listener)
    try:
        yield statements
    finally:
        event.remove(Engine, "before_cursor_execute", _listener)


@contextmanager
def _inject_sql_failure_on(substring: str) -> Iterator[None]:
    triggered = False

    def _listener(
        conn: Any,
        cursor: Any,
        statement: str,
        parameters: Any,
        context: Any,
        executemany: bool,
    ) -> None:
        nonlocal triggered
        if not triggered and substring in statement.lower():
            triggered = True
            raise RuntimeError(f"Simulated mid-transaction failure on: {substring}")

    event.listen(Engine, "before_cursor_execute", _listener)
    try:
        yield
    finally:
        event.remove(Engine, "before_cursor_execute", _listener)


def _assert_uniform_error_response(
    response: httpx.Response,
    expected_status: int,
    expected_code: str,
) -> dict[str, Any]:
    assert response.status_code == expected_status
    body = response.json()
    assert set(body.keys()) == {"code", "message", "details"}
    assert "detail" not in body
    assert body["code"] == expected_code
    assert isinstance(body["message"], str) and body["message"]
    return body


@pytest.mark.asyncio
async def test_create_sale_single_payment_and_frozen_snapshots(
    sales_auth_env: None,
    db_session: AsyncSession,
) -> None:
    """Scenario: Successful sale registration with single payment method and frozen snapshots."""
    user_id = str(uuid.uuid4())
    business_id = str(uuid.uuid4())

    async with db_session.begin():
        await _seed_business(db_session, business_id)
        await _seed_business_user(db_session, business_id, user_id, role="owner")
        product_id = await _seed_product(
            db_session,
            business_id=business_id,
            name="Cafe 500g",
            sale_price=Decimal("1500.00"),
            cost_price=Decimal("900.00"),
            stock=Decimal("10.00"),
        )

    client_id = str(uuid.uuid4())
    cookies = _make_jwt_cookie(user_id=user_id, business_id=business_id, role="owner")
    try:
        transport = httpx.ASGITransport(app=app)
        with _capture_sql_statements() as sql_log:
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    SALES_URL,
                    cookies=cookies,
                    json={
                        "client_id": client_id,
                        "items": [{"product_id": product_id, "quantity": "2.00"}],
                        "payments": [{"payment_method": "cash", "amount": "3000.00"}],
                    },
                )

        assert response.status_code == 201
        body = response.json()
        assert uuid.UUID(body["id"])
        assert body["client_id"] == client_id
        assert body["total_amount"] == "3000.00"
        assert body["created_at"] is not None
        assert len(body["items"]) == 1
        item = body["items"][0]
        assert uuid.UUID(item["id"])
        assert item["product_id"] == product_id
        assert item["product_name"] == "Cafe 500g"
        assert item["quantity"] == "2.00"
        assert item["unit_price"] == "1500.00"
        assert item["subtotal"] == "3000.00"
        assert "unit_cost" not in item
        assert len(body["payments"]) == 1
        assert body["payments"][0]["payment_method"] == "cash"
        assert body["payments"][0]["amount"] == "3000.00"

        insert_idx = next(i for i, (stmt, _) in enumerate(sql_log) if "insert into sales" in stmt)
        assert any("set local role app_api" in stmt for stmt, _ in sql_log[:insert_idx])
        assert any(
            "set_config" in stmt and "app.current_business_id" in stmt and business_id in params
            for stmt, params in sql_log[:insert_idx]
        )

        # Update product price and cost after sale, then verify frozen snapshot in DB
        async with db_session.begin():
            await db_session.execute(
                text(
                    """
                    UPDATE products
                    SET sale_price = 2000.00, cost_price = 1100.00
                    WHERE id = :pid
                    """
                ),
                {"pid": product_id},
            )
            stock_val = (
                await db_session.execute(
                    text("SELECT stock FROM products WHERE id = :pid"),
                    {"pid": product_id},
                )
            ).scalar_one()
            assert stock_val == Decimal("8.00")

            sale_row = (
                (
                    await db_session.execute(
                        text("SELECT total_amount FROM sales WHERE id = :sid"),
                        {"sid": body["id"]},
                    )
                )
                .mappings()
                .one()
            )
            assert sale_row["total_amount"] == Decimal("3000.00")

            item_row = (
                (
                    await db_session.execute(
                        text(
                            """
                            SELECT quantity, unit_price, unit_cost
                            FROM sale_items
                            WHERE sale_id = :sid
                            """
                        ),
                        {"sid": body["id"]},
                    )
                )
                .mappings()
                .one()
            )
            assert item_row["quantity"] == Decimal("2.00")
            assert item_row["unit_price"] == Decimal("1500.00")
            assert item_row["unit_cost"] == Decimal("900.00")
    finally:
        await _cleanup_businesses(db_session, [business_id])


@pytest.mark.asyncio
async def test_create_sale_combined_payments_exact_decimal_sum(
    sales_auth_env: None,
    db_session: AsyncSession,
) -> None:
    """Scenario: Successful sale registration with combined payment methods
    and exact decimal sum.
    """
    user_id = str(uuid.uuid4())
    business_id = str(uuid.uuid4())

    async with db_session.begin():
        await _seed_business(db_session, business_id)
        await _seed_business_user(db_session, business_id, user_id, role="owner")
        p1 = await _seed_product(
            db_session,
            business_id=business_id,
            name="Caramelo A",
            sale_price=Decimal("0.10"),
            cost_price=Decimal("0.05"),
            stock=Decimal("5.00"),
        )
        p2 = await _seed_product(
            db_session,
            business_id=business_id,
            name="Caramelo B",
            sale_price=Decimal("0.20"),
            cost_price=Decimal("0.10"),
            stock=Decimal("4.00"),
        )

    client_id = str(uuid.uuid4())
    cookies = _make_jwt_cookie(user_id=user_id, business_id=business_id, role="owner")
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                SALES_URL,
                cookies=cookies,
                json={
                    "client_id": client_id,
                    "items": [
                        {"product_id": p1, "quantity": "1.00"},
                        {"product_id": p2, "quantity": "1.00"},
                    ],
                    "payments": [
                        {"payment_method": "cash", "amount": "0.10"},
                        {"payment_method": "card", "amount": "0.10"},
                        {"payment_method": "transfer", "amount": "0.10"},
                    ],
                },
            )

        assert response.status_code == 201
        body = response.json()
        assert body["total_amount"] == "0.30"
        assert [(p["payment_method"], p["amount"]) for p in body["payments"]] == [
            ("cash", "0.10"),
            ("card", "0.10"),
            ("transfer", "0.10"),
        ]

        async with db_session.begin():
            rows = (
                (
                    await db_session.execute(
                        text("SELECT id, stock FROM products WHERE id IN (:p1, :p2)"),
                        {"p1": p1, "p2": p2},
                    )
                )
                .mappings()
                .all()
            )
            stock_by_id = {str(r["id"]): r["stock"] for r in rows}
            assert stock_by_id[p1] == Decimal("4.00")
            assert stock_by_id[p2] == Decimal("3.00")
    finally:
        await _cleanup_businesses(db_session, [business_id])


@pytest.mark.asyncio
async def test_fractional_quantity_rounding_and_duplicate_product_lines(
    sales_auth_env: None,
    db_session: AsyncSession,
) -> None:
    """Scenario: Fractional quantity rounding and duplicate product lines
    aggregate stock deduction cleanly.
    """
    user_id = str(uuid.uuid4())
    business_id = str(uuid.uuid4())

    async with db_session.begin():
        await _seed_business(db_session, business_id)
        await _seed_business_user(db_session, business_id, user_id, role="owner")
        product_id = await _seed_product(
            db_session,
            business_id=business_id,
            name="Queso Fraccionado",
            sale_price=Decimal("100.33"),
            cost_price=Decimal("60.00"),
            stock=Decimal("5.00"),
        )

    cookies = _make_jwt_cookie(user_id=user_id, business_id=business_id, role="owner")
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # 1.50 * 100.33 = 150.495 -> ROUND_HALF_UP -> 150.50
            resp_frac = await client.post(
                SALES_URL,
                cookies=cookies,
                json={
                    "client_id": str(uuid.uuid4()),
                    "items": [{"product_id": product_id, "quantity": "1.50"}],
                    "payments": [{"payment_method": "cash", "amount": "150.50"}],
                },
            )
            # Duplicate product lines: 1.00 (100.33) + 2.00 (200.66) = 300.99
            resp_dup = await client.post(
                SALES_URL,
                cookies=cookies,
                json={
                    "client_id": str(uuid.uuid4()),
                    "items": [
                        {"product_id": product_id, "quantity": "1.00"},
                        {"product_id": product_id, "quantity": "2.00"},
                    ],
                    "payments": [{"payment_method": "cash", "amount": "300.99"}],
                },
            )

        assert resp_frac.status_code == 201
        assert resp_frac.json()["total_amount"] == "150.50"
        assert resp_frac.json()["items"][0]["subtotal"] == "150.50"

        assert resp_dup.status_code == 201
        assert resp_dup.json()["total_amount"] == "300.99"

        async with db_session.begin():
            stock_val = (
                await db_session.execute(
                    text("SELECT stock FROM products WHERE id = :pid"),
                    {"pid": product_id},
                )
            ).scalar_one()
            # 5.00 - 1.50 - (1.00 + 2.00) = 0.50
            assert stock_val == Decimal("0.50")
    finally:
        await _cleanup_businesses(db_session, [business_id])


@pytest.mark.asyncio
async def test_counter_sale_succeeds_when_stock_becomes_negative(
    sales_auth_env: None,
    db_session: AsyncSession,
) -> None:
    """Scenario: Counter sale succeeds when stock becomes negative."""
    user_id = str(uuid.uuid4())
    business_id = str(uuid.uuid4())

    async with db_session.begin():
        await _seed_business(db_session, business_id)
        await _seed_business_user(db_session, business_id, user_id, role="owner")
        p_pos = await _seed_product(
            db_session,
            business_id=business_id,
            name="Gaseosa",
            sale_price=Decimal("500.00"),
            stock=Decimal("2.00"),
        )
        p_neg = await _seed_product(
            db_session,
            business_id=business_id,
            name="Pan",
            sale_price=Decimal("400.00"),
            stock=Decimal("-1.00"),
        )

    cookies = _make_jwt_cookie(user_id=user_id, business_id=business_id, role="owner")
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp1 = await client.post(
                SALES_URL,
                cookies=cookies,
                json={
                    "client_id": str(uuid.uuid4()),
                    "items": [{"product_id": p_pos, "quantity": "3.00"}],
                    "payments": [{"payment_method": "cash", "amount": "1500.00"}],
                },
            )
            resp2 = await client.post(
                SALES_URL,
                cookies=cookies,
                json={
                    "client_id": str(uuid.uuid4()),
                    "items": [{"product_id": p_neg, "quantity": "2.00"}],
                    "payments": [{"payment_method": "cash", "amount": "800.00"}],
                },
            )

        assert resp1.status_code == 201
        assert resp2.status_code == 201

        async with db_session.begin():
            rows = (
                (
                    await db_session.execute(
                        text("SELECT id, stock FROM products WHERE id IN (:p1, :p2)"),
                        {"p1": p_pos, "p2": p_neg},
                    )
                )
                .mappings()
                .all()
            )
            stock_by_id = {str(r["id"]): r["stock"] for r in rows}
            assert stock_by_id[p_pos] == Decimal("-1.00")
            assert stock_by_id[p_neg] == Decimal("-3.00")
    finally:
        await _cleanup_businesses(db_session, [business_id])


@pytest.mark.asyncio
async def test_transactional_rollback_on_mid_transaction_failure(
    sales_auth_env: None,
    db_session: AsyncSession,
) -> None:
    """Scenario: Transactional rollback restores database state on mid-transaction failure."""
    user_id = str(uuid.uuid4())
    business_id = str(uuid.uuid4())

    async with db_session.begin():
        await _seed_business(db_session, business_id)
        await _seed_business_user(db_session, business_id, user_id, role="owner")
        product_id = await _seed_product(
            db_session,
            business_id=business_id,
            name="Yerba Rollback",
            sale_price=Decimal("1000.00"),
            stock=Decimal("10.00"),
        )

    cookies = _make_jwt_cookie(user_id=user_id, business_id=business_id, role="owner")
    try:
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        with _inject_sql_failure_on("insert into payments"):
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    SALES_URL,
                    cookies=cookies,
                    json={
                        "client_id": str(uuid.uuid4()),
                        "items": [{"product_id": product_id, "quantity": "2.00"}],
                        "payments": [{"payment_method": "cash", "amount": "2000.00"}],
                    },
                )

        assert response.status_code == 500

        async with db_session.begin():
            stock_val = (
                await db_session.execute(
                    text("SELECT stock FROM products WHERE id = :pid"),
                    {"pid": product_id},
                )
            ).scalar_one()
            assert stock_val == Decimal("10.00")

            for table_name in ("sales", "sale_items", "payments"):
                count = (
                    await db_session.execute(
                        text(f"SELECT count(*) FROM {table_name} WHERE business_id = :b_id"),
                        {"b_id": business_id},
                    )
                ).scalar_one()
                assert count == 0, f"{table_name} should have 0 rows after rollback"
    finally:
        await _cleanup_businesses(db_session, [business_id])


@pytest.mark.asyncio
async def test_sequential_idempotent_retry_returns_200_even_after_catalog_change(
    sales_auth_env: None,
    db_session: AsyncSession,
) -> None:
    """Scenario: Sequential retry with identical client_id returns 200 without
    duplicating records or re-deducting stock.
    """
    user_id = str(uuid.uuid4())
    business_id = str(uuid.uuid4())

    async with db_session.begin():
        await _seed_business(db_session, business_id)
        await _seed_business_user(db_session, business_id, user_id, role="owner")
        product_id = await _seed_product(
            db_session,
            business_id=business_id,
            name="Azucar 1kg",
            sale_price=Decimal("1000.00"),
            cost_price=Decimal("600.00"),
            stock=Decimal("10.00"),
        )

    client_id = str(uuid.uuid4())
    cookies = _make_jwt_cookie(user_id=user_id, business_id=business_id, role="owner")
    payload = {
        "client_id": client_id,
        "items": [{"product_id": product_id, "quantity": "2.00"}],
        "payments": [{"payment_method": "cash", "amount": "2000.00"}],
    }
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            first_resp = await client.post(SALES_URL, cookies=cookies, json=payload)
            assert first_resp.status_code == 201

            # Edit price and deactivate product after original sale
            async with db_session.begin():
                await db_session.execute(
                    text(
                        """
                        UPDATE products
                        SET sale_price = 1800.00, is_active = false
                        WHERE id = :pid
                        """
                    ),
                    {"pid": product_id},
                )

            retry_resp = await client.post(SALES_URL, cookies=cookies, json=payload)
            assert retry_resp.status_code == 200
            assert retry_resp.json() == first_resp.json()

        async with db_session.begin():
            sales_count = (
                await db_session.execute(
                    text(
                        """
                        SELECT count(*) FROM sales
                        WHERE business_id = :b_id AND client_id = :c_id
                        """
                    ),
                    {"b_id": business_id, "c_id": client_id},
                )
            ).scalar_one()
            assert sales_count == 1

            stock_val = (
                await db_session.execute(
                    text("SELECT stock FROM products WHERE id = :pid"),
                    {"pid": product_id},
                )
            ).scalar_one()
            assert stock_val == Decimal("8.00")
    finally:
        await _cleanup_businesses(db_session, [business_id])


@pytest.mark.asyncio
async def test_concurrent_idempotent_retries_deduct_stock_once(
    sales_auth_env: None,
    db_session: AsyncSession,
) -> None:
    """Scenario: Concurrent retries with identical client_id produce a single
    sale and single stock deduction.
    """
    user_id = str(uuid.uuid4())
    business_id = str(uuid.uuid4())

    async with db_session.begin():
        await _seed_business(db_session, business_id)
        await _seed_business_user(db_session, business_id, user_id, role="owner")
        product_id = await _seed_product(
            db_session,
            business_id=business_id,
            name="Aceite 900ml",
            sale_price=Decimal("1200.00"),
            stock=Decimal("10.00"),
        )

    client_id = str(uuid.uuid4())
    cookies = _make_jwt_cookie(user_id=user_id, business_id=business_id, role="owner")
    payload = {
        "client_id": client_id,
        "items": [{"product_id": product_id, "quantity": "3.00"}],
        "payments": [{"payment_method": "transfer", "amount": "3600.00"}],
    }
    try:
        transport = httpx.ASGITransport(app=app)
        async with (
            httpx.AsyncClient(transport=transport, base_url="http://test") as c1,
            httpx.AsyncClient(transport=transport, base_url="http://test") as c2,
        ):
            r1, r2 = await asyncio.gather(
                c1.post(SALES_URL, cookies=cookies, json=payload),
                c2.post(SALES_URL, cookies=cookies, json=payload),
            )

        assert sorted([r1.status_code, r2.status_code]) == [200, 201]
        assert r1.json() == r2.json()

        async with db_session.begin():
            sales_count = (
                await db_session.execute(
                    text(
                        """
                        SELECT count(*) FROM sales
                        WHERE business_id = :b_id AND client_id = :c_id
                        """
                    ),
                    {"b_id": business_id, "c_id": client_id},
                )
            ).scalar_one()
            assert sales_count == 1

            stock_val = (
                await db_session.execute(
                    text("SELECT stock FROM products WHERE id = :pid"),
                    {"pid": product_id},
                )
            ).scalar_one()
            assert stock_val == Decimal("7.00")
    finally:
        await _cleanup_businesses(db_session, [business_id])


@pytest.mark.asyncio
async def test_same_client_id_allowed_across_distinct_businesses(
    sales_auth_env: None,
    db_session: AsyncSession,
) -> None:
    """Scenario: Same client_id allowed across distinct businesses without
    cross-tenant collision.
    """
    business_a = str(uuid.uuid4())
    business_b = str(uuid.uuid4())
    owner_a = str(uuid.uuid4())
    owner_b = str(uuid.uuid4())
    shared_client_id = str(uuid.uuid4())

    async with db_session.begin():
        await _seed_business(db_session, business_a, name="Negocio A")
        await _seed_business(db_session, business_b, name="Negocio B")
        await _seed_business_user(db_session, business_a, owner_a, role="owner")
        await _seed_business_user(db_session, business_b, owner_b, role="owner")
        prod_a = await _seed_product(
            db_session,
            business_id=business_a,
            name="Prod A",
            sale_price=Decimal("100.00"),
        )
        prod_b = await _seed_product(
            db_session,
            business_id=business_b,
            name="Prod B",
            sale_price=Decimal("250.00"),
        )

    cookies_a = _make_jwt_cookie(user_id=owner_a, business_id=business_a, role="owner")
    cookies_b = _make_jwt_cookie(user_id=owner_b, business_id=business_b, role="owner")
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp_a = await client.post(
                SALES_URL,
                cookies=cookies_a,
                json={
                    "client_id": shared_client_id,
                    "items": [{"product_id": prod_a, "quantity": "1.00"}],
                    "payments": [{"payment_method": "cash", "amount": "100.00"}],
                },
            )
            resp_b = await client.post(
                SALES_URL,
                cookies=cookies_b,
                json={
                    "client_id": shared_client_id,
                    "items": [{"product_id": prod_b, "quantity": "1.00"}],
                    "payments": [{"payment_method": "card", "amount": "250.00"}],
                },
            )

        assert resp_a.status_code == 201
        assert resp_b.status_code == 201
        assert resp_a.json()["id"] != resp_b.json()["id"]
        assert resp_b.json()["total_amount"] == "250.00"
    finally:
        await _cleanup_businesses(db_session, [business_a, business_b])


@pytest.mark.asyncio
@pytest.mark.parametrize("payment_amount", ["2999.99", "3000.01"])
async def test_reject_payment_total_mismatch(
    sales_auth_env: None,
    db_session: AsyncSession,
    payment_amount: str,
) -> None:
    """Scenario: Rejection of payment total mismatch against server-calculated sale total."""
    user_id = str(uuid.uuid4())
    business_id = str(uuid.uuid4())

    async with db_session.begin():
        await _seed_business(db_session, business_id)
        await _seed_business_user(db_session, business_id, user_id, role="owner")
        product_id = await _seed_product(
            db_session,
            business_id=business_id,
            name="Producto Mismatch",
            sale_price=Decimal("1500.00"),
            stock=Decimal("10.00"),
        )

    cookies = _make_jwt_cookie(user_id=user_id, business_id=business_id, role="owner")
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                SALES_URL,
                cookies=cookies,
                json={
                    "client_id": str(uuid.uuid4()),
                    "items": [{"product_id": product_id, "quantity": "2.00"}],
                    "payments": [{"payment_method": "cash", "amount": payment_amount}],
                },
            )

        _assert_uniform_error_response(response, 422, "PAYMENT_TOTAL_MISMATCH")

        async with db_session.begin():
            stock_val = (
                await db_session.execute(
                    text("SELECT stock FROM products WHERE id = :pid"),
                    {"pid": product_id},
                )
            ).scalar_one()
            assert stock_val == Decimal("10.00")
            sales_count = (
                await db_session.execute(
                    text("SELECT count(*) FROM sales WHERE business_id = :b_id"),
                    {"b_id": business_id},
                )
            ).scalar_one()
            assert sales_count == 0
    finally:
        await _cleanup_businesses(db_session, [business_id])


@pytest.mark.asyncio
async def test_reject_inactive_product_for_new_sale(
    sales_auth_env: None,
    db_session: AsyncSession,
) -> None:
    """Scenario: Rejection of inactive product for new sale creation."""
    user_id = str(uuid.uuid4())
    business_id = str(uuid.uuid4())

    async with db_session.begin():
        await _seed_business(db_session, business_id)
        await _seed_business_user(db_session, business_id, user_id, role="owner")
        product_id = await _seed_product(
            db_session,
            business_id=business_id,
            name="Producto Desactivado",
            sale_price=Decimal("500.00"),
            stock=Decimal("10.00"),
            is_active=False,
        )

    cookies = _make_jwt_cookie(user_id=user_id, business_id=business_id, role="owner")
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                SALES_URL,
                cookies=cookies,
                json={
                    "client_id": str(uuid.uuid4()),
                    "items": [{"product_id": product_id, "quantity": "1.00"}],
                    "payments": [{"payment_method": "cash", "amount": "500.00"}],
                },
            )

        _assert_uniform_error_response(response, 422, "PRODUCT_INACTIVE")

        async with db_session.begin():
            stock_val = (
                await db_session.execute(
                    text("SELECT stock FROM products WHERE id = :pid"),
                    {"pid": product_id},
                )
            ).scalar_one()
            assert stock_val == Decimal("10.00")
            sales_count = (
                await db_session.execute(
                    text("SELECT count(*) FROM sales WHERE business_id = :b_id"),
                    {"b_id": business_id},
                )
            ).scalar_one()
            assert sales_count == 0
    finally:
        await _cleanup_businesses(db_session, [business_id])


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "bad_qty,bad_amount",
    [
        (1.5, "10.00"),
        ("1.00", 10.5),
        (True, "10.00"),
        ("1.00", False),
        ("NaN", "10.00"),
        ("Infinity", "10.00"),
        ("1.00", "-Infinity"),
        ("1.234", "10.00"),
        ("1.00", "10.999"),
        ("0.00", "10.00"),
        ("-1.00", "10.00"),
        ("1.00", "0.00"),
        ("1.00", "-5.00"),
        ("10000000000.00", "10.00"),
        ("1.00", "10000000000.00"),
    ],
)
async def test_reject_float_bool_nonfinite_scale_nonpositive_and_overflow(
    sales_auth_env: None,
    bad_qty: Any,
    bad_amount: Any,
) -> None:
    """Scenario: Rejection of float values, excessive decimal places,
    non-positive amounts, and overflow.
    """
    cookies = _make_jwt_cookie(
        user_id=str(uuid.uuid4()),
        business_id=str(uuid.uuid4()),
        role="owner",
    )
    transport = httpx.ASGITransport(app=app)
    with _capture_sql_statements() as sql_log:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                SALES_URL,
                cookies=cookies,
                json={
                    "client_id": str(uuid.uuid4()),
                    "items": [{"product_id": str(uuid.uuid4()), "quantity": bad_qty}],
                    "payments": [{"payment_method": "cash", "amount": bad_amount}],
                },
            )

    _assert_uniform_error_response(response, 422, "VALIDATION_ERROR")
    assert not any("insert into sales" in stmt for stmt, _ in sql_log)


@pytest.mark.asyncio
async def test_reject_sale_total_rounding_to_zero_or_overflow(
    sales_auth_env: None,
    db_session: AsyncSession,
) -> None:
    """Scenario: Rejection of inputs whose product total rounds to 0.00 or
    overflows numeric(12,2).
    """
    user_id = str(uuid.uuid4())
    business_id = str(uuid.uuid4())

    async with db_session.begin():
        await _seed_business(db_session, business_id)
        await _seed_business_user(db_session, business_id, user_id, role="owner")
        p_tiny = await _seed_product(
            db_session,
            business_id=business_id,
            name="Centavo",
            sale_price=Decimal("0.01"),
            stock=Decimal("10.00"),
        )
        p_huge = await _seed_product(
            db_session,
            business_id=business_id,
            name="Caro",
            sale_price=Decimal("9999999999.99"),
            stock=Decimal("10.00"),
        )

    cookies = _make_jwt_cookie(user_id=user_id, business_id=business_id, role="owner")
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp_zero = await client.post(
                SALES_URL,
                cookies=cookies,
                json={
                    "client_id": str(uuid.uuid4()),
                    "items": [{"product_id": p_tiny, "quantity": "0.01"}],
                    "payments": [{"payment_method": "cash", "amount": "0.01"}],
                },
            )
            resp_overflow = await client.post(
                SALES_URL,
                cookies=cookies,
                json={
                    "client_id": str(uuid.uuid4()),
                    "items": [{"product_id": p_huge, "quantity": "2.00"}],
                    "payments": [{"payment_method": "cash", "amount": "9999999999.99"}],
                },
            )

        _assert_uniform_error_response(resp_zero, 422, "VALIDATION_ERROR")
        _assert_uniform_error_response(resp_overflow, 422, "VALIDATION_ERROR")
    finally:
        await _cleanup_businesses(db_session, [business_id])


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {
            "client_id": str(uuid.uuid4()),
            "items": [],
            "payments": [{"payment_method": "cash", "amount": "10.00"}],
        },
        {
            "client_id": str(uuid.uuid4()),
            "items": [{"product_id": str(uuid.uuid4()), "quantity": "1.00"}],
            "payments": [],
        },
        {
            "client_id": str(uuid.uuid4()),
            "items": [{"product_id": str(uuid.uuid4()), "quantity": "1.00"}],
            "payments": [{"payment_method": "other", "amount": "10.00"}],
        },
        {
            "client_id": str(uuid.uuid4()),
            "items": [{"product_id": str(uuid.uuid4()), "quantity": "1.00"}],
            "payments": [{"payment_method": "CASH", "amount": "10.00"}],
        },
        {
            "client_id": str(uuid.uuid4()),
            "items": [{"product_id": str(uuid.uuid4()), "quantity": "1.00"}],
            "payments": [{"payment_method": "crypto", "amount": "10.00"}],
        },
        {
            "client_id": "not-a-uuid",
            "items": [{"product_id": str(uuid.uuid4()), "quantity": "1.00"}],
            "payments": [{"payment_method": "cash", "amount": "10.00"}],
        },
        {
            "client_id": str(uuid.uuid4()),
            "items": [{"product_id": "not-a-uuid", "quantity": "1.00"}],
            "payments": [{"payment_method": "cash", "amount": "10.00"}],
        },
        {
            "client_id": f"{uuid.uuid4()}\x00",
            "items": [{"product_id": str(uuid.uuid4()), "quantity": "1.00"}],
            "payments": [{"payment_method": "cash", "amount": "10.00"}],
        },
        {
            "client_id": str(uuid.uuid4()),
            "items": [{"product_id": f"{uuid.uuid4()}\x00", "quantity": "1.00"}],
            "payments": [{"payment_method": "cash", "amount": "10.00"}],
        },
        {
            "client_id": str(uuid.uuid4()),
            "items": [{"product_id": str(uuid.uuid4()), "quantity": "1.00"}],
            "payments": [{"payment_method": "cash\x00", "amount": "10.00"}],
        },
    ],
)
async def test_reject_empty_lists_invalid_method_invalid_uuid_or_nul_bytes(
    sales_auth_env: None,
    payload: dict[str, Any],
) -> None:
    """Scenario: Rejection of empty items, empty payments, invalid payment
    method, invalid UUID, or NUL bytes.
    """
    cookies = _make_jwt_cookie(
        user_id=str(uuid.uuid4()),
        business_id=str(uuid.uuid4()),
        role="owner",
    )
    transport = httpx.ASGITransport(app=app)
    with _capture_sql_statements() as sql_log:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(SALES_URL, cookies=cookies, json=payload)

    _assert_uniform_error_response(response, 422, "VALIDATION_ERROR")
    assert not any("insert into sales" in stmt for stmt, _ in sql_log)


@pytest.mark.asyncio
async def test_unauthenticated_and_onboarding_pending_rejected(sales_auth_env: None) -> None:
    """Scenario: Unauthenticated or onboarding-pending requests rejected with 401 and 403."""
    onboarding_cookies = _make_jwt_cookie(
        user_id=str(uuid.uuid4()),
        business_id=None,
        role=None,
    )
    valid_body = {
        "client_id": str(uuid.uuid4()),
        "items": [{"product_id": str(uuid.uuid4()), "quantity": "1.00"}],
        "payments": [{"payment_method": "cash", "amount": "10.00"}],
    }
    transport = httpx.ASGITransport(app=app)
    with _capture_sql_statements() as sql_log:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            unauth_resp = await client.post(SALES_URL, json=valid_body)
            onb_resp = await client.post(SALES_URL, cookies=onboarding_cookies, json=valid_body)

    _assert_uniform_error_response(unauth_resp, 401, "UNAUTHENTICATED")
    _assert_uniform_error_response(onb_resp, 403, "ONBOARDING_REQUIRED")
    assert not any("sales" in stmt for stmt, _ in sql_log)


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["owner", "cashier"])
async def test_owner_and_cashier_authorized_without_exposing_unit_cost(
    sales_auth_env: None,
    db_session: AsyncSession,
    role: str,
) -> None:
    """Scenario: Both owner and cashier roles authorized to register sales
    without exposing unit_cost.
    """
    user_id = str(uuid.uuid4())
    business_id = str(uuid.uuid4())

    async with db_session.begin():
        await _seed_business(db_session, business_id)
        await _seed_business_user(db_session, business_id, user_id, role=role)
        product_id = await _seed_product(
            db_session,
            business_id=business_id,
            name="Alfajor",
            sale_price=Decimal("800.00"),
            cost_price=Decimal("450.00"),
            stock=Decimal("10.00"),
        )

    cookies = _make_jwt_cookie(user_id=user_id, business_id=business_id, role=role)
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                SALES_URL,
                cookies=cookies,
                json={
                    "client_id": str(uuid.uuid4()),
                    "items": [{"product_id": product_id, "quantity": "2.00"}],
                    "payments": [{"payment_method": "cash", "amount": "1600.00"}],
                },
            )

        assert response.status_code == 201
        body = response.json()
        item = body["items"][0]
        assert item["unit_price"] == "800.00"
        assert item["subtotal"] == "1600.00"
        assert "unit_cost" not in item
    finally:
        await _cleanup_businesses(db_session, [business_id])


@pytest.mark.asyncio
async def test_cross_tenant_or_missing_product_rejected_404_and_body_business_id_ignored(
    sales_auth_env: None,
    db_session: AsyncSession,
) -> None:
    """Scenario: Cross-tenant or non-existent product rejected with 404 and
    body business_id ignored.
    """
    business_a = str(uuid.uuid4())
    business_b = str(uuid.uuid4())
    owner_a = str(uuid.uuid4())

    async with db_session.begin():
        await _seed_business(db_session, business_a, name="Negocio A")
        await _seed_business(db_session, business_b, name="Negocio B")
        await _seed_business_user(db_session, business_a, owner_a, role="owner")
        prod_a = await _seed_product(
            db_session,
            business_id=business_a,
            name="Producto A",
            sale_price=Decimal("100.00"),
            stock=Decimal("10.00"),
        )
        prod_b = await _seed_product(
            db_session,
            business_id=business_b,
            name="Producto B Secreto",
            sale_price=Decimal("200.00"),
            stock=Decimal("10.00"),
        )

    cookies_a = _make_jwt_cookie(user_id=owner_a, business_id=business_a, role="owner")
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            cross_resp = await client.post(
                SALES_URL,
                cookies=cookies_a,
                json={
                    "client_id": str(uuid.uuid4()),
                    "items": [{"product_id": prod_b, "quantity": "1.00"}],
                    "payments": [{"payment_method": "cash", "amount": "200.00"}],
                },
            )
            missing_resp = await client.post(
                SALES_URL,
                cookies=cookies_a,
                json={
                    "client_id": str(uuid.uuid4()),
                    "items": [{"product_id": str(uuid.uuid4()), "quantity": "1.00"}],
                    "payments": [{"payment_method": "cash", "amount": "100.00"}],
                },
            )
            valid_with_spoofed_business = await client.post(
                SALES_URL,
                cookies=cookies_a,
                json={
                    "business_id": business_b,
                    "client_id": str(uuid.uuid4()),
                    "items": [{"product_id": prod_a, "quantity": "1.00"}],
                    "payments": [{"payment_method": "cash", "amount": "100.00"}],
                },
            )

        _assert_uniform_error_response(cross_resp, 404, "PRODUCT_NOT_FOUND")
        _assert_uniform_error_response(missing_resp, 404, "PRODUCT_NOT_FOUND")

        assert valid_with_spoofed_business.status_code == 201
        created_sale_id = valid_with_spoofed_business.json()["id"]

        async with db_session.begin():
            stock_b = (
                await db_session.execute(
                    text("SELECT stock FROM products WHERE id = :pid"),
                    {"pid": prod_b},
                )
            ).scalar_one()
            assert stock_b == Decimal("10.00")

            sale_biz = (
                await db_session.execute(
                    text("SELECT business_id FROM sales WHERE id = :sid"),
                    {"sid": created_sale_id},
                )
            ).scalar_one()
            assert str(sale_biz) == business_a
    finally:
        await _cleanup_businesses(db_session, [business_a, business_b])


@pytest.mark.asyncio
async def test_openapi_documents_sales_routes_and_schemas() -> None:
    """Scenario: Sales route and schemas documented in OpenAPI schema."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/openapi.json")

    assert response.status_code == 200
    spec = response.json()
    assert SALES_URL in spec["paths"]
    path_item = spec["paths"][SALES_URL]
    assert "post" in path_item
    assert "sales" in path_item["post"]["tags"]

    post_responses = set(path_item["post"]["responses"].keys())
    assert {"200", "201", "401", "403", "404", "422"}.issubset(post_responses)

    schemas = spec["components"]["schemas"]
    for schema_name in (
        "SaleCreate",
        "SaleItemCreate",
        "SalePaymentCreate",
        "SaleResponse",
        "SaleItemResponse",
        "SalePaymentResponse",
        "ErrorResponse",
    ):
        assert schema_name in schemas

    assert "unit_cost" not in schemas["SaleItemResponse"]["properties"]

    openapi_path = Path(__file__).resolve().parents[3] / "docs" / "api" / "openapi.json"
    assert check_openapi(openapi_path) == 0
