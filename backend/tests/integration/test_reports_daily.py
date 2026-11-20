"""Integration and contract tests for GET /api/v1/reports/daily."""

import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import httpx
import jwt
import pytest
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.main import app

pytestmark = pytest.mark.reportes

TEST_JWT_SECRET = "test-jwt-secret-key-for-reports-tests-32b"
REPORTS_DAILY_URL = "/api/v1/reports/daily"


@pytest.fixture
def reports_auth_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
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
    *,
    name: str = "Kiosco Reportes",
    country: str = "AR",
    timezone: str = "America/Argentina/Buenos_Aires",
) -> None:
    # Migration 0004 hardened businesses_onboarding_insert:
    # requires current_user_id + current_business_id.
    await db_session.execute(text(f"SET LOCAL app.current_user_id = '{uuid.uuid4()}';"))
    await db_session.execute(text(f"SET LOCAL app.current_business_id = '{business_id}';"))
    await db_session.execute(
        text(
            """
            INSERT INTO businesses (id, name, country, timezone)
            VALUES (:id, :name, :country, :timezone)
            """
        ),
        {"id": business_id, "name": name, "country": country, "timezone": timezone},
    )


async def _seed_business_user(
    db_session: AsyncSession,
    business_id: str,
    user_id: str,
    role: str = "owner",
) -> None:
    # Migration 0004 hardened business_users_insert_own_user: requires user_id + business_id GUCs.
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


async def _seed_product(
    db_session: AsyncSession,
    *,
    business_id: str,
    name: str,
    sale_price: Decimal = Decimal("100.00"),
    cost_price: Decimal = Decimal("50.00"),
    stock: Decimal = Decimal("10.00"),
    product_id: str | None = None,
) -> str:
    pid = product_id or str(uuid.uuid4())
    # Migration 0004: requires current_user_id + current_business_id GUCs for products INSERT.
    await db_session.execute(text(f"SET LOCAL app.current_user_id = '{uuid.uuid4()}';"))
    await db_session.execute(text(f"SET LOCAL app.current_business_id = '{business_id}';"))
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


async def _seed_sale(
    db_session: AsyncSession,
    *,
    business_id: str,
    total_amount: Decimal,
    created_at: datetime | None = None,
    sale_id: str | None = None,
) -> str:
    sid = sale_id or str(uuid.uuid4())
    cid = str(uuid.uuid4())
    # Migration 0004: requires current_user_id + current_business_id GUCs for sales INSERT.
    await db_session.execute(text(f"SET LOCAL app.current_user_id = '{uuid.uuid4()}';"))
    await db_session.execute(text(f"SET LOCAL app.current_business_id = '{business_id}';"))
    if created_at is None:
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
    else:
        await db_session.execute(
            text(
                """
                INSERT INTO sales (id, business_id, client_id, total_amount, created_at)
                VALUES (:id, :business_id, :client_id, :total_amount, :created_at)
                """
            ),
            {
                "id": sid,
                "business_id": business_id,
                "client_id": cid,
                "total_amount": total_amount,
                "created_at": created_at,
            },
        )
    return sid


async def _seed_sale_item(
    db_session: AsyncSession,
    *,
    business_id: str,
    sale_id: str,
    product_id: str,
    quantity: Decimal,
    unit_price: Decimal,
    unit_cost: Decimal,
) -> str:
    iid = str(uuid.uuid4())
    # Migration 0004: requires current_user_id + current_business_id GUCs for sale_items INSERT.
    await db_session.execute(text(f"SET LOCAL app.current_user_id = '{uuid.uuid4()}';"))
    await db_session.execute(text(f"SET LOCAL app.current_business_id = '{business_id}';"))
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


async def _seed_payment(
    db_session: AsyncSession,
    *,
    business_id: str,
    sale_id: str,
    payment_method: str,
    amount: Decimal,
) -> str:
    pay_id = str(uuid.uuid4())
    # Migration 0004: requires current_user_id + current_business_id GUCs for payments INSERT.
    await db_session.execute(text(f"SET LOCAL app.current_user_id = '{uuid.uuid4()}';"))
    await db_session.execute(text(f"SET LOCAL app.current_business_id = '{business_id}';"))
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


async def _cleanup_businesses(db_session: AsyncSession, business_ids: list[str]) -> None:
    if not business_ids:
        return
    async with db_session.begin():
        for b_id in business_ids:
            await db_session.execute(
                text("DELETE FROM payments WHERE business_id = :id"),
                {"id": b_id},
            )
            await db_session.execute(
                text("DELETE FROM sale_items WHERE business_id = :id"),
                {"id": b_id},
            )
            await db_session.execute(
                text("DELETE FROM sales WHERE business_id = :id"),
                {"id": b_id},
            )
            await db_session.execute(
                text("DELETE FROM products WHERE business_id = :id"),
                {"id": b_id},
            )
            await db_session.execute(
                text("DELETE FROM business_users WHERE business_id = :id"),
                {"id": b_id},
            )
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
async def test_daily_report_aggregates_sales_without_fan_out(
    reports_auth_env: None,
    db_session: AsyncSession,
) -> None:
    """Scenario: Daily report aggregates sales, costs, margin,
    and payment breakdown for a day with sales.
    """
    owner_id = str(uuid.uuid4())
    business_id = str(uuid.uuid4())
    target_date = "2026-11-19"

    async with db_session.begin():
        await _seed_business(
            db_session,
            business_id,
            timezone="America/Argentina/Buenos_Aires",
        )
        await _seed_business_user(db_session, business_id, owner_id, role="owner")
        prod_a = await _seed_product(
            db_session,
            business_id=business_id,
            name="Yerba",
            sale_price=Decimal("200.00"),
            cost_price=Decimal("120.00"),
        )
        prod_b = await _seed_product(
            db_session,
            business_id=business_id,
            name="Azucar",
            sale_price=Decimal("100.00"),
            cost_price=Decimal("60.00"),
        )

        # Sale 1: 2 items AND 2 payments (cash + card) -> tests anti-fan-out!
        # total_amount = 500.00; cost = 2*120 + 1*60 = 300.00
        sale_1 = await _seed_sale(
            db_session,
            business_id=business_id,
            total_amount=Decimal("500.00"),
            created_at=datetime(2026, 11, 19, 15, 0, 0, tzinfo=UTC),
        )
        await _seed_sale_item(
            db_session,
            business_id=business_id,
            sale_id=sale_1,
            product_id=prod_a,
            quantity=Decimal("2.00"),
            unit_price=Decimal("200.00"),
            unit_cost=Decimal("120.00"),
        )
        await _seed_sale_item(
            db_session,
            business_id=business_id,
            sale_id=sale_1,
            product_id=prod_b,
            quantity=Decimal("1.00"),
            unit_price=Decimal("100.00"),
            unit_cost=Decimal("60.00"),
        )
        await _seed_payment(
            db_session,
            business_id=business_id,
            sale_id=sale_1,
            payment_method="cash",
            amount=Decimal("300.00"),
        )
        await _seed_payment(
            db_session,
            business_id=business_id,
            sale_id=sale_1,
            payment_method="card",
            amount=Decimal("200.00"),
        )

        # Sale 2: 2 items AND 2 payments (transfer + cash)
        # total_amount = 300.00; cost = 1*120 + 1*60 = 180.00
        sale_2 = await _seed_sale(
            db_session,
            business_id=business_id,
            total_amount=Decimal("300.00"),
            created_at=datetime(2026, 11, 19, 18, 30, 0, tzinfo=UTC),
        )
        await _seed_sale_item(
            db_session,
            business_id=business_id,
            sale_id=sale_2,
            product_id=prod_a,
            quantity=Decimal("1.00"),
            unit_price=Decimal("200.00"),
            unit_cost=Decimal("120.00"),
        )
        await _seed_sale_item(
            db_session,
            business_id=business_id,
            sale_id=sale_2,
            product_id=prod_b,
            quantity=Decimal("1.00"),
            unit_price=Decimal("100.00"),
            unit_cost=Decimal("60.00"),
        )
        await _seed_payment(
            db_session,
            business_id=business_id,
            sale_id=sale_2,
            payment_method="transfer",
            amount=Decimal("250.00"),
        )
        await _seed_payment(
            db_session,
            business_id=business_id,
            sale_id=sale_2,
            payment_method="cash",
            amount=Decimal("50.00"),
        )

    cookies = _make_jwt_cookie(user_id=owner_id, business_id=business_id, role="owner")
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
            cookies=cookies,
        ) as client:
            response = await client.get(REPORTS_DAILY_URL, params={"date": target_date})

        assert response.status_code == 200
        body = response.json()
        assert body == {
            "date": target_date,
            "timezone": "America/Argentina/Buenos_Aires",
            "total_sales": "800.00",
            "transactions_count": 2,
            "total_cost": "480.00",
            "gross_margin": "320.00",
            "margin_percentage": "40.00",
            "payment_breakdown": {
                "cash": "350.00",
                "card": "200.00",
                "transfer": "250.00",
            },
        }
    finally:
        await _cleanup_businesses(db_session, [business_id])


@pytest.mark.asyncio
async def test_daily_report_groups_sales_strictly_by_business_iana_timezone(
    reports_auth_env: None,
    db_session: AsyncSession,
) -> None:
    """Scenario: Sales near UTC midnight are grouped strictly by the business IANA timezone."""
    owner_id = str(uuid.uuid4())
    business_id = str(uuid.uuid4())
    target_date = "2026-11-19"

    async with db_session.begin():
        await _seed_business(
            db_session,
            business_id,
            timezone="America/Argentina/Buenos_Aires",  # UTC-3
        )
        await _seed_business_user(db_session, business_id, owner_id, role="owner")
        prod_id = await _seed_product(
            db_session,
            business_id=business_id,
            name="Cafe",
            sale_price=Decimal("100.00"),
            cost_price=Decimal("40.00"),
        )

        # 2026-11-19 02:30:00Z -> 2026-11-18 23:30:00-03:00 (previous local day -> EXCLUDED)
        s_prev = await _seed_sale(
            db_session,
            business_id=business_id,
            total_amount=Decimal("999.00"),
            created_at=datetime(2026, 11, 19, 2, 30, 0, tzinfo=UTC),
        )
        await _seed_sale_item(
            db_session,
            business_id=business_id,
            sale_id=s_prev,
            product_id=prod_id,
            quantity=Decimal("1.00"),
            unit_price=Decimal("999.00"),
            unit_cost=Decimal("100.00"),
        )
        await _seed_payment(
            db_session,
            business_id=business_id,
            sale_id=s_prev,
            payment_method="cash",
            amount=Decimal("999.00"),
        )

        # 2026-11-19 03:00:00Z -> 2026-11-19 00:00:00-03:00 (exact start of target day -> INCLUDED)
        s_start = await _seed_sale(
            db_session,
            business_id=business_id,
            total_amount=Decimal("100.00"),
            created_at=datetime(2026, 11, 19, 3, 0, 0, tzinfo=UTC),
        )
        await _seed_sale_item(
            db_session,
            business_id=business_id,
            sale_id=s_start,
            product_id=prod_id,
            quantity=Decimal("1.00"),
            unit_price=Decimal("100.00"),
            unit_cost=Decimal("40.00"),
        )
        await _seed_payment(
            db_session,
            business_id=business_id,
            sale_id=s_start,
            payment_method="cash",
            amount=Decimal("100.00"),
        )

        # 2026-11-20 02:59:59Z -> 2026-11-19 23:59:59-03:00 (exact end of target day -> INCLUDED)
        s_end = await _seed_sale(
            db_session,
            business_id=business_id,
            total_amount=Decimal("200.00"),
            created_at=datetime(2026, 11, 20, 2, 59, 59, tzinfo=UTC),
        )
        await _seed_sale_item(
            db_session,
            business_id=business_id,
            sale_id=s_end,
            product_id=prod_id,
            quantity=Decimal("2.00"),
            unit_price=Decimal("100.00"),
            unit_cost=Decimal("40.00"),
        )
        await _seed_payment(
            db_session,
            business_id=business_id,
            sale_id=s_end,
            payment_method="card",
            amount=Decimal("200.00"),
        )

        # 2026-11-20 03:00:00Z -> 2026-11-20 00:00:00-03:00 (next local day -> EXCLUDED)
        s_next = await _seed_sale(
            db_session,
            business_id=business_id,
            total_amount=Decimal("777.00"),
            created_at=datetime(2026, 11, 20, 3, 0, 0, tzinfo=UTC),
        )
        await _seed_sale_item(
            db_session,
            business_id=business_id,
            sale_id=s_next,
            product_id=prod_id,
            quantity=Decimal("1.00"),
            unit_price=Decimal("777.00"),
            unit_cost=Decimal("100.00"),
        )
        await _seed_payment(
            db_session,
            business_id=business_id,
            sale_id=s_next,
            payment_method="transfer",
            amount=Decimal("777.00"),
        )

    cookies = _make_jwt_cookie(user_id=owner_id, business_id=business_id, role="owner")
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
            cookies=cookies,
        ) as client:
            response = await client.get(REPORTS_DAILY_URL, params={"date": target_date})

        assert response.status_code == 200
        body = response.json()
        assert body["date"] == target_date
        assert body["timezone"] == "America/Argentina/Buenos_Aires"
        assert body["transactions_count"] == 2
        assert body["total_sales"] == "300.00"
        assert body["total_cost"] == "120.00"
        assert body["gross_margin"] == "180.00"
        assert body["margin_percentage"] == "60.00"
        assert body["payment_breakdown"] == {
            "cash": "100.00",
            "card": "200.00",
            "transfer": "0.00",
        }
    finally:
        await _cleanup_businesses(db_session, [business_id])


@pytest.mark.asyncio
async def test_daily_report_omitted_date_defaults_to_business_local_date(
    reports_auth_env: None,
    db_session: AsyncSession,
) -> None:
    """Scenario: Omitted date query parameter defaults to current
    local date in business timezone.
    """
    owner_id = str(uuid.uuid4())
    business_id = str(uuid.uuid4())
    tz = "America/Santiago"

    async with db_session.begin():
        await _seed_business(db_session, business_id, country="CL", timezone=tz)
        await _seed_business_user(db_session, business_id, owner_id, role="owner")
        prod_id = await _seed_product(
            db_session,
            business_id=business_id,
            name="Pan",
            sale_price=Decimal("250.00"),
            cost_price=Decimal("100.00"),
        )
        sale_id = await _seed_sale(
            db_session,
            business_id=business_id,
            total_amount=Decimal("250.00"),
        )
        await _seed_sale_item(
            db_session,
            business_id=business_id,
            sale_id=sale_id,
            product_id=prod_id,
            quantity=Decimal("1.00"),
            unit_price=Decimal("250.00"),
            unit_cost=Decimal("100.00"),
        )
        await _seed_payment(
            db_session,
            business_id=business_id,
            sale_id=sale_id,
            payment_method="transfer",
            amount=Decimal("250.00"),
        )
        expected_local_date = (
            await db_session.execute(
                text("SELECT (now() AT TIME ZONE :tz)::date::text"),
                {"tz": tz},
            )
        ).scalar_one()

    cookies = _make_jwt_cookie(user_id=owner_id, business_id=business_id, role="owner")
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
            cookies=cookies,
        ) as client:
            response = await client.get(REPORTS_DAILY_URL)

        assert response.status_code == 200
        body = response.json()
        assert body["date"] == expected_local_date
        assert body["timezone"] == tz
        assert body["transactions_count"] == 1
        assert body["total_sales"] == "250.00"
        assert body["total_cost"] == "100.00"
        assert body["gross_margin"] == "150.00"
        assert body["margin_percentage"] == "60.00"
        assert body["payment_breakdown"] == {
            "cash": "0.00",
            "card": "0.00",
            "transfer": "250.00",
        }
    finally:
        await _cleanup_businesses(db_session, [business_id])


@pytest.mark.asyncio
async def test_daily_report_day_without_sales_returns_zeros_without_nulls(
    reports_auth_env: None,
    db_session: AsyncSession,
) -> None:
    """Scenario: Day without sales returns zero totals without nulls or division by zero."""
    owner_id = str(uuid.uuid4())
    business_id = str(uuid.uuid4())
    empty_date = "2026-11-18"

    async with db_session.begin():
        await _seed_business(
            db_session,
            business_id,
            timezone="America/Argentina/Buenos_Aires",
        )
        await _seed_business_user(db_session, business_id, owner_id, role="owner")
        # Seed a sale on a different date to verify it does not bleed into empty_date
        await _seed_sale(
            db_session,
            business_id=business_id,
            total_amount=Decimal("500.00"),
            created_at=datetime(2026, 11, 19, 15, 0, 0, tzinfo=UTC),
        )

    cookies = _make_jwt_cookie(user_id=owner_id, business_id=business_id, role="owner")
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
            cookies=cookies,
        ) as client:
            response = await client.get(REPORTS_DAILY_URL, params={"date": empty_date})

        assert response.status_code == 200
        body = response.json()
        assert body == {
            "date": empty_date,
            "timezone": "America/Argentina/Buenos_Aires",
            "total_sales": "0.00",
            "transactions_count": 0,
            "total_cost": "0.00",
            "gross_margin": "0.00",
            "margin_percentage": "0.00",
            "payment_breakdown": {
                "cash": "0.00",
                "card": "0.00",
                "transfer": "0.00",
            },
        }
        for key, value in body.items():
            assert value is not None, f"Field {key} must not be null"
        for key, value in body["payment_breakdown"].items():
            assert value is not None, f"payment_breakdown.{key} must not be null"
    finally:
        await _cleanup_businesses(db_session, [business_id])


@pytest.mark.asyncio
async def test_daily_report_preserves_frozen_unit_cost_and_decimal_precision(
    reports_auth_env: None,
    db_session: AsyncSession,
) -> None:
    """Scenario: Frozen unit_cost snapshot and fractional quantities
    preserved after product cost changes.
    """
    owner_id = str(uuid.uuid4())
    business_id = str(uuid.uuid4())
    target_date = "2026-11-19"

    async with db_session.begin():
        await _seed_business(db_session, business_id)
        await _seed_business_user(db_session, business_id, owner_id, role="owner")
        prod_frac = await _seed_product(
            db_session,
            business_id=business_id,
            name="Queso",
            sale_price=Decimal("100.00"),
            cost_price=Decimal("10.05"),
        )
        prod_zero_cost = await _seed_product(
            db_session,
            business_id=business_id,
            name="Bolsa",
            sale_price=Decimal("5.00"),
            cost_price=Decimal("0.00"),
        )

        # 0.50 * 10.05 = 5.025 -> quantized ROUND_HALF_UP to 5.03
        # + 1.00 * 0.00 = 0.00
        # total_sales = 55.00, total_cost = 5.03, gross_margin = 49.97
        # margin_percentage = (49.97 / 55.00) * 100 = 90.854545... -> "90.85"
        sale_id = await _seed_sale(
            db_session,
            business_id=business_id,
            total_amount=Decimal("55.00"),
            created_at=datetime(2026, 11, 19, 14, 0, 0, tzinfo=UTC),
        )
        await _seed_sale_item(
            db_session,
            business_id=business_id,
            sale_id=sale_id,
            product_id=prod_frac,
            quantity=Decimal("0.50"),
            unit_price=Decimal("100.00"),
            unit_cost=Decimal("10.05"),
        )
        await _seed_sale_item(
            db_session,
            business_id=business_id,
            sale_id=sale_id,
            product_id=prod_zero_cost,
            quantity=Decimal("1.00"),
            unit_price=Decimal("5.00"),
            unit_cost=Decimal("0.00"),
        )
        await _seed_payment(
            db_session,
            business_id=business_id,
            sale_id=sale_id,
            payment_method="cash",
            amount=Decimal("55.00"),
        )

        # Mutate products.cost_price AFTER the sale; report must still use frozen unit_cost
        await db_session.execute(
            text("UPDATE products SET cost_price = 999.99 WHERE id = :id"),
            {"id": prod_frac},
        )
        await db_session.execute(
            text("UPDATE products SET cost_price = 50.00 WHERE id = :id"),
            {"id": prod_zero_cost},
        )

    cookies = _make_jwt_cookie(user_id=owner_id, business_id=business_id, role="owner")
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
            cookies=cookies,
        ) as client:
            response = await client.get(REPORTS_DAILY_URL, params={"date": target_date})

        assert response.status_code == 200
        body = response.json()
        assert body["total_sales"] == "55.00"
        assert body["total_cost"] == "5.03"
        assert body["gross_margin"] == "49.97"
        assert body["margin_percentage"] == "90.85"
    finally:
        await _cleanup_businesses(db_session, [business_id])


@pytest.mark.asyncio
async def test_daily_report_negative_gross_margin_serialized_accurately(
    reports_auth_env: None,
    db_session: AsyncSession,
) -> None:
    """Scenario: Negative gross margin and negative profitability serialized accurately."""
    owner_id = str(uuid.uuid4())
    business_id = str(uuid.uuid4())
    target_date = "2026-11-19"

    async with db_session.begin():
        await _seed_business(db_session, business_id)
        await _seed_business_user(db_session, business_id, owner_id, role="owner")
        prod_id = await _seed_product(
            db_session,
            business_id=business_id,
            name="Liquidacion",
            sale_price=Decimal("100.00"),
            cost_price=Decimal("150.00"),
        )
        sale_id = await _seed_sale(
            db_session,
            business_id=business_id,
            total_amount=Decimal("100.00"),
            created_at=datetime(2026, 11, 19, 16, 0, 0, tzinfo=UTC),
        )
        await _seed_sale_item(
            db_session,
            business_id=business_id,
            sale_id=sale_id,
            product_id=prod_id,
            quantity=Decimal("1.00"),
            unit_price=Decimal("100.00"),
            unit_cost=Decimal("150.00"),
        )
        await _seed_payment(
            db_session,
            business_id=business_id,
            sale_id=sale_id,
            payment_method="cash",
            amount=Decimal("100.00"),
        )

    cookies = _make_jwt_cookie(user_id=owner_id, business_id=business_id, role="owner")
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
            cookies=cookies,
        ) as client:
            response = await client.get(REPORTS_DAILY_URL, params={"date": target_date})

        assert response.status_code == 200
        body = response.json()
        assert body["total_sales"] == "100.00"
        assert body["total_cost"] == "150.00"
        assert body["gross_margin"] == "-50.00"
        assert body["margin_percentage"] == "-50.00"
    finally:
        await _cleanup_businesses(db_session, [business_id])


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "bad_date",
    [
        "",
        "not-a-date",
        "19-11-2026",
        "2026-02-30",
        "2026-11-19T12:00:00",
        "1969-12-31",
        "2101-01-01",
        "2026-11-19\x00",
    ],
)
async def test_daily_report_rejects_invalid_date_query_with_422_before_db(
    reports_auth_env: None,
    bad_date: str,
) -> None:
    """Scenario: Malformed, empty, out-of-bounds, or NUL-byte date query rejected with 422."""
    cookies = _make_jwt_cookie(
        user_id=str(uuid.uuid4()),
        business_id=str(uuid.uuid4()),
        role="owner",
    )
    transport = httpx.ASGITransport(app=app)
    with _capture_sql_statements() as sql_log:
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
            cookies=cookies,
        ) as client:
            response = await client.get(REPORTS_DAILY_URL, params={"date": bad_date})

    _assert_uniform_error_response(response, 422, "VALIDATION_ERROR")
    assert sql_log == []


@pytest.mark.asyncio
async def test_daily_report_unauthenticated_and_onboarding_pending_rejected(
    reports_auth_env: None,
) -> None:
    """Scenario: Unauthenticated or onboarding-pending requests rejected with 401 and 403."""
    onboarding_cookies = _make_jwt_cookie(
        user_id=str(uuid.uuid4()),
        business_id=None,
        role=None,
    )
    transport = httpx.ASGITransport(app=app)
    with _capture_sql_statements() as sql_log:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            unauth_resp = await client.get(REPORTS_DAILY_URL)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
            cookies=onboarding_cookies,
        ) as client:
            onb_resp = await client.get(REPORTS_DAILY_URL)

    _assert_uniform_error_response(unauth_resp, 401, "UNAUTHENTICATED")
    _assert_uniform_error_response(onb_resp, 403, "ONBOARDING_REQUIRED")
    assert sql_log == []


@pytest.mark.asyncio
async def test_daily_report_non_owner_role_denied_with_403_before_db(
    reports_auth_env: None,
) -> None:
    """Scenario: Non-owner role denied access to daily report with 403 Forbidden."""
    cashier_cookies = _make_jwt_cookie(
        user_id=str(uuid.uuid4()),
        business_id=str(uuid.uuid4()),
        role="cashier",
    )
    transport = httpx.ASGITransport(app=app)
    with _capture_sql_statements() as sql_log:
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
            cookies=cashier_cookies,
        ) as client:
            response = await client.get(REPORTS_DAILY_URL)

    _assert_uniform_error_response(response, 403, "FORBIDDEN")
    assert sql_log == []


@pytest.mark.asyncio
async def test_daily_report_tenant_isolation_rls_and_ignore_query_business_id(
    reports_auth_env: None,
    db_session: AsyncSession,
) -> None:
    """Scenario: Tenant isolation enforced via RLS excludes other
    businesses and ignores query business_id.
    """
    business_a = str(uuid.uuid4())
    business_b = str(uuid.uuid4())
    owner_a = str(uuid.uuid4())
    target_date = "2026-11-19"

    async with db_session.begin():
        await _seed_business(db_session, business_a, name="Tenant A")
        await _seed_business(db_session, business_b, name="Tenant B")
        await _seed_business_user(db_session, business_a, owner_a, role="owner")

        prod_a = await _seed_product(db_session, business_id=business_a, name="Prod A")
        prod_b = await _seed_product(db_session, business_id=business_b, name="Prod B")

        sale_a = await _seed_sale(
            db_session,
            business_id=business_a,
            total_amount=Decimal("100.00"),
            created_at=datetime(2026, 11, 19, 15, 0, 0, tzinfo=UTC),
        )
        await _seed_sale_item(
            db_session,
            business_id=business_a,
            sale_id=sale_a,
            product_id=prod_a,
            quantity=Decimal("1.00"),
            unit_price=Decimal("100.00"),
            unit_cost=Decimal("40.00"),
        )
        await _seed_payment(
            db_session,
            business_id=business_a,
            sale_id=sale_a,
            payment_method="cash",
            amount=Decimal("100.00"),
        )

        sale_b = await _seed_sale(
            db_session,
            business_id=business_b,
            total_amount=Decimal("9000.00"),
            created_at=datetime(2026, 11, 19, 15, 0, 0, tzinfo=UTC),
        )
        await _seed_sale_item(
            db_session,
            business_id=business_b,
            sale_id=sale_b,
            product_id=prod_b,
            quantity=Decimal("1.00"),
            unit_price=Decimal("9000.00"),
            unit_cost=Decimal("1000.00"),
        )
        await _seed_payment(
            db_session,
            business_id=business_b,
            sale_id=sale_b,
            payment_method="transfer",
            amount=Decimal("9000.00"),
        )

    cookies_a = _make_jwt_cookie(user_id=owner_a, business_id=business_a, role="owner")
    try:
        transport = httpx.ASGITransport(app=app)
        with _capture_sql_statements() as sql_log:
            async with httpx.AsyncClient(
                transport=transport,
                base_url="http://test",
                cookies=cookies_a,
            ) as client:
                response = await client.get(
                    REPORTS_DAILY_URL,
                    params={"date": target_date, "business_id": business_b},
                )

        assert response.status_code == 200
        body = response.json()
        assert body["transactions_count"] == 1
        assert body["total_sales"] == "100.00"
        assert body["total_cost"] == "40.00"
        assert body["gross_margin"] == "60.00"
        assert body["payment_breakdown"] == {
            "cash": "100.00",
            "card": "0.00",
            "transfer": "0.00",
        }

        report_idx = next(i for i, (stmt, _) in enumerate(sql_log) if "from businesses" in stmt)
        assert any("set local role app_api" in stmt for stmt, _ in sql_log[:report_idx])
        assert any(
            "set_config" in stmt and "app.current_business_id" in stmt and business_a in params
            for stmt, params in sql_log[:report_idx]
        )
    finally:
        await _cleanup_businesses(db_session, [business_a, business_b])


@pytest.mark.asyncio
async def test_daily_report_nonexistent_business_returns_404(
    reports_auth_env: None,
) -> None:
    """Scenario: Non-existent business under RLS returns 404 Not Found."""
    cookies = _make_jwt_cookie(
        user_id=str(uuid.uuid4()),
        business_id=str(uuid.uuid4()),
        role="owner",
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
        cookies=cookies,
    ) as client:
        response = await client.get(REPORTS_DAILY_URL, params={"date": "2026-11-19"})

    _assert_uniform_error_response(response, 404, "BUSINESS_NOT_FOUND")


@pytest.mark.asyncio
async def test_openapi_documents_daily_report_route_and_schemas() -> None:
    """Scenario: Daily report route and schemas documented in OpenAPI and static export."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/openapi.json")

    assert response.status_code == 200
    spec = response.json()
    assert REPORTS_DAILY_URL in spec["paths"]
    path_item = spec["paths"][REPORTS_DAILY_URL]
    assert "get" in path_item
    get_op = path_item["get"]
    assert "reports" in get_op["tags"]

    param_names = {p["name"] for p in get_op.get("parameters", [])}
    assert "date" in param_names

    responses = set(get_op["responses"].keys())
    assert {"200", "401", "403", "404", "422"}.issubset(responses)

    schemas = spec["components"]["schemas"]
    assert "DailyReportResponse" in schemas
    assert "PaymentMethodBreakdown" in schemas
    assert "ErrorResponse" in schemas
