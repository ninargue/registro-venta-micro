import time
import uuid
from collections.abc import AsyncGenerator, Iterator
from contextlib import contextmanager
from decimal import Decimal
from typing import Any

import httpx
import jwt
import pytest
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_tenant_db
from app.main import app

TEST_JWT_SECRET = "test-jwt-secret-key-for-catalog-tests-32b"
CATALOG_PRODUCTS_URL = "/api/v1/catalog/products"


@pytest.fixture
def catalog_auth_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
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
    name: str = "Kiosco Catalogo",
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
async def test_create_product_with_all_attributes(
    catalog_auth_env: None,
    db_session: AsyncSession,
) -> None:
    """Scenario: Successful product creation with all attributes."""
    user_id = str(uuid.uuid4())
    business_id = str(uuid.uuid4())

    async with db_session.begin():
        await _seed_business(db_session, business_id)
        await _seed_business_user(db_session, business_id, user_id, role="owner")

    cookies = _make_jwt_cookie(user_id=user_id, business_id=business_id, role="owner")
    try:
        transport = httpx.ASGITransport(app=app)
        with _capture_sql_statements() as sql_log:
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    CATALOG_PRODUCTS_URL,
                    cookies=cookies,
                    json={
                        "code": "  SKU-001  ",
                        "name": "  Yerba Mate 1kg  ",
                        "sale_price": "3500.50",
                        "cost_price": "2200.00",
                        "stock": "10.00",
                    },
                )

        assert response.status_code == 201
        body = response.json()
        assert uuid.UUID(body["id"])
        assert body["code"] == "SKU-001"
        assert body["name"] == "Yerba Mate 1kg"
        assert body["sale_price"] == "3500.50"
        assert body["cost_price"] == "2200.00"
        assert body["stock"] == "10.00"
        assert body["is_active"] is True
        assert body["created_at"] is not None
        assert body["updated_at"] is not None

        insert_idx = next(
            i for i, (stmt, _) in enumerate(sql_log) if "insert into products" in stmt
        )
        assert any("set local role app_api" in stmt for stmt, _ in sql_log[:insert_idx])
        assert any(
            "set_config" in stmt and "app.current_business_id" in stmt and business_id in params
            for stmt, params in sql_log[:insert_idx]
        )

        async with db_session.begin():
            row = (
                (
                    await db_session.execute(
                        text("SELECT business_id FROM products WHERE id = :id"),
                        {"id": body["id"]},
                    )
                )
                .mappings()
                .one()
            )
            assert str(row["business_id"]) == business_id
    finally:
        await _cleanup_businesses(db_session, [business_id])


@pytest.mark.asyncio
async def test_create_product_with_defaults_for_optional_fields(
    catalog_auth_env: None,
    db_session: AsyncSession,
) -> None:
    """Scenario: Successful product creation with defaults for optional fields."""
    user_id = str(uuid.uuid4())
    business_id = str(uuid.uuid4())

    async with db_session.begin():
        await _seed_business(db_session, business_id)
        await _seed_business_user(db_session, business_id, user_id, role="owner")

    cookies = _make_jwt_cookie(user_id=user_id, business_id=business_id, role="owner")
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                CATALOG_PRODUCTS_URL,
                cookies=cookies,
                json={"name": "Agua Mineral 500ml", "sale_price": "950.00"},
            )

        assert response.status_code == 201
        body = response.json()
        assert body["code"] is None
        assert body["name"] == "Agua Mineral 500ml"
        assert body["sale_price"] == "950.00"
        assert body["cost_price"] == "0.00"
        assert body["stock"] == "0.00"
        assert body["is_active"] is True
    finally:
        await _cleanup_businesses(db_session, [business_id])


@pytest.mark.asyncio
async def test_create_multiple_products_without_code_in_same_business(
    catalog_auth_env: None,
    db_session: AsyncSession,
) -> None:
    """Scenario: Multiple products without code allowed in the same business."""
    user_id = str(uuid.uuid4())
    business_id = str(uuid.uuid4())

    async with db_session.begin():
        await _seed_business(db_session, business_id)
        await _seed_business_user(db_session, business_id, user_id, role="owner")
        await _seed_product(db_session, business_id=business_id, name="Pan Casero", code=None)

    cookies = _make_jwt_cookie(user_id=user_id, business_id=business_id, role="owner")
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp_omitted = await client.post(
                CATALOG_PRODUCTS_URL,
                cookies=cookies,
                json={"name": "Facturas", "sale_price": "1200.00"},
            )
            resp_null = await client.post(
                CATALOG_PRODUCTS_URL,
                cookies=cookies,
                json={"code": None, "name": "Medialunas", "sale_price": "1500.00"},
            )

        assert resp_omitted.status_code == 201
        assert resp_omitted.json()["code"] is None
        assert resp_null.status_code == 201
        assert resp_null.json()["code"] is None
    finally:
        await _cleanup_businesses(db_session, [business_id])


@pytest.mark.asyncio
async def test_create_same_product_code_across_distinct_businesses(
    catalog_auth_env: None,
    db_session: AsyncSession,
) -> None:
    """Scenario: Same product code allowed across distinct businesses."""
    business_a = str(uuid.uuid4())
    business_b = str(uuid.uuid4())
    owner_b = str(uuid.uuid4())

    async with db_session.begin():
        await _seed_business(db_session, business_a, name="Negocio A")
        await _seed_business(db_session, business_b, name="Negocio B")
        await _seed_business_user(db_session, business_b, owner_b, role="owner")
        await _seed_product(
            db_session,
            business_id=business_a,
            code="SHARED-01",
            name="Producto A",
        )

    cookies_b = _make_jwt_cookie(user_id=owner_b, business_id=business_b, role="owner")
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                CATALOG_PRODUCTS_URL,
                cookies=cookies_b,
                json={"code": "SHARED-01", "name": "Producto B", "sale_price": "500.00"},
            )

        assert response.status_code == 201
        body = response.json()
        assert body["code"] == "SHARED-01"

        async with db_session.begin():
            row = (
                (
                    await db_session.execute(
                        text("SELECT business_id FROM products WHERE id = :id"),
                        {"id": body["id"]},
                    )
                )
                .mappings()
                .one()
            )
            assert str(row["business_id"]) == business_b
    finally:
        await _cleanup_businesses(db_session, [business_a, business_b])


@pytest.mark.asyncio
async def test_create_duplicate_non_null_code_same_business_returns_409(
    catalog_auth_env: None,
    db_session: AsyncSession,
) -> None:
    """Scenario: Duplicate non-null product code in the same business returns 409 Conflict."""
    user_id = str(uuid.uuid4())
    business_id = str(uuid.uuid4())

    async with db_session.begin():
        await _seed_business(db_session, business_id)
        await _seed_business_user(db_session, business_id, user_id, role="owner")
        await _seed_product(
            db_session,
            business_id=business_id,
            code="DUP-01",
            name="Original",
        )

    cookies = _make_jwt_cookie(user_id=user_id, business_id=business_id, role="owner")
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            dup_resp = await client.post(
                CATALOG_PRODUCTS_URL,
                cookies=cookies,
                json={"code": "  DUP-01  ", "name": "Duplicado", "sale_price": "200.00"},
            )
            _assert_uniform_error_response(dup_resp, 409, "PRODUCT_CODE_ALREADY_EXISTS")

            # Verify session/app remains healthy for subsequent requests
            list_resp = await client.get(CATALOG_PRODUCTS_URL, cookies=cookies)
            assert list_resp.status_code == 200
            assert list_resp.json()["total"] == 1
    finally:
        await _cleanup_businesses(db_session, [business_id])


@pytest.mark.asyncio
async def test_duplicate_code_409_uses_savepoint_and_keeps_outer_transaction_healthy(
    catalog_auth_env: None,
    db_session: AsyncSession,
) -> None:
    """Scenario: Duplicate product code 409 uses a savepoint (begin_nested)
    so the outer transaction is not aborted with InFailedSQLTransactionError.
    """
    user_id = str(uuid.uuid4())
    business_id = str(uuid.uuid4())

    async with db_session.begin():
        await _seed_business(db_session, business_id)
        await _seed_business_user(db_session, business_id, user_id, role="owner")
        await _seed_product(
            db_session,
            business_id=business_id,
            code="DUP-SP-01",
            name="Original Savepoint",
        )

    async def _override_get_tenant_db() -> AsyncGenerator[AsyncSession]:
        yield db_session

    cookies = _make_jwt_cookie(user_id=user_id, business_id=business_id, role="owner")
    app.dependency_overrides[get_tenant_db] = _override_get_tenant_db
    try:
        async with db_session.begin():
            await db_session.execute(text("SET LOCAL ROLE app_api"))
            await db_session.execute(
                text("SELECT set_config('app.current_business_id', :b_id, true)"),
                {"b_id": business_id},
            )
            await db_session.execute(
                text("SELECT set_config('app.current_user_id', :u_id, true)"),
                {"u_id": user_id},
            )

            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                dup_resp = await client.post(
                    CATALOG_PRODUCTS_URL,
                    cookies=cookies,
                    json={"code": "DUP-SP-01", "name": "Duplicado", "sale_price": "200.00"},
                )
                _assert_uniform_error_response(dup_resp, 409, "PRODUCT_CODE_ALREADY_EXISTS")

                # Without begin_nested(), the outer transaction would be aborted
                # (InFailedSQLTransactionError) on any subsequent SQL statement.
                count_result = await db_session.execute(
                    text("SELECT COUNT(*) FROM products WHERE business_id = :b_id"),
                    {"b_id": business_id},
                )
                assert count_result.scalar_one() == 1

                list_resp = await client.get(CATALOG_PRODUCTS_URL, cookies=cookies)
                assert list_resp.status_code == 200
                assert list_resp.json()["total"] == 1
    finally:
        app.dependency_overrides.pop(get_tenant_db, None)
        await _cleanup_businesses(db_session, [business_id])


@pytest.mark.asyncio
async def test_exact_decimal_persistence_and_string_serialization(
    catalog_auth_env: None,
    db_session: AsyncSession,
) -> None:
    """Scenario: Exact Decimal persistence and string serialization without floating-point drift."""
    user_id = str(uuid.uuid4())
    business_id = str(uuid.uuid4())

    async with db_session.begin():
        await _seed_business(db_session, business_id)
        await _seed_business_user(db_session, business_id, user_id, role="owner")

    cookies = _make_jwt_cookie(user_id=user_id, business_id=business_id, role="owner")
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp_str = await client.post(
                CATALOG_PRODUCTS_URL,
                cookies=cookies,
                json={
                    "name": "Decimal Exacto",
                    "sale_price": "19.99",
                    "cost_price": "0.10",
                    "stock": "0.20",
                },
            )
            resp_int = await client.post(
                CATALOG_PRODUCTS_URL,
                cookies=cookies,
                json={
                    "name": "Entero Normalizado",
                    "sale_price": 100,
                    "cost_price": 0,
                    "stock": 5,
                },
            )

        assert resp_str.status_code == 201
        body_str = resp_str.json()
        assert body_str["sale_price"] == "19.99"
        assert body_str["cost_price"] == "0.10"
        assert body_str["stock"] == "0.20"

        assert resp_int.status_code == 201
        body_int = resp_int.json()
        assert body_int["sale_price"] == "100.00"
        assert body_int["cost_price"] == "0.00"
        assert body_int["stock"] == "5.00"
    finally:
        await _cleanup_businesses(db_session, [business_id])


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {"name": "Float Sale", "sale_price": 19.99},
        {"name": "Float Cost", "sale_price": "10.00", "cost_price": 5.5},
        {"name": "Float Stock", "sale_price": "10.00", "stock": 1.25},
        {"name": "Bool Sale", "sale_price": True},
        {"name": "Bool Cost", "sale_price": "10.00", "cost_price": False},
        {"name": "Bool Stock", "sale_price": "10.00", "stock": True},
        {"name": "NaN Sale", "sale_price": "NaN"},
        {"name": "Inf Cost", "sale_price": "10.00", "cost_price": "Infinity"},
        {"name": "NegInf Stock", "sale_price": "10.00", "stock": "-Infinity"},
        {"name": "Scale Sale", "sale_price": "12.345"},
        {"name": "Scale Cost", "sale_price": "10.00", "cost_price": "1.234"},
        {"name": "Scale Stock", "sale_price": "10.00", "stock": "0.001"},
    ],
)
async def test_reject_float_bool_nonfinite_and_excessive_decimal_places(
    catalog_auth_env: None,
    payload: dict[str, Any],
) -> None:
    """Scenario: Rejection of float values and excessive decimal places
    on monetary and stock fields.
    """
    cookies = _make_jwt_cookie(
        user_id=str(uuid.uuid4()),
        business_id=str(uuid.uuid4()),
        role="owner",
    )
    transport = httpx.ASGITransport(app=app)
    with _capture_sql_statements() as sql_log:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(CATALOG_PRODUCTS_URL, cookies=cookies, json=payload)

    _assert_uniform_error_response(response, 422, "VALIDATION_ERROR")
    assert not any("insert into products" in stmt for stmt, _ in sql_log)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {"name": "Zero Price", "sale_price": "0.00"},
        {"name": "Negative Price", "sale_price": "-1.00"},
        {"name": "Negative Cost", "sale_price": "10.00", "cost_price": "-0.01"},
        {"name": "Negative Stock", "sale_price": "10.00", "stock": "-0.01"},
        {"name": "Null Cost", "sale_price": "10.00", "cost_price": None},
        {"name": "Null Stock", "sale_price": "10.00", "stock": None},
        {"name": "Overflow Sale", "sale_price": "10000000000.00"},
        {"name": "Overflow Cost", "sale_price": "10.00", "cost_price": "10000000000.00"},
        {"name": "Overflow Stock", "sale_price": "10.00", "stock": "10000000000.00"},
    ],
)
async def test_reject_invalid_prices_negative_initial_stock_or_overflow(
    catalog_auth_env: None,
    payload: dict[str, Any],
) -> None:
    """Scenario: Rejection of invalid prices, negative initial stock, or numeric overflow."""
    cookies = _make_jwt_cookie(
        user_id=str(uuid.uuid4()),
        business_id=str(uuid.uuid4()),
        role="owner",
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(CATALOG_PRODUCTS_URL, cookies=cookies, json=payload)

    _assert_uniform_error_response(response, 422, "VALIDATION_ERROR")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {"name": "", "sale_price": "10.00"},
        {"name": "   ", "sale_price": "10.00"},
        {"name": "Valid", "code": "", "sale_price": "10.00"},
        {"name": "Valid", "code": "   ", "sale_price": "10.00"},
        {"name": "a" * 151, "sale_price": "10.00"},
        {"name": "Valid", "code": "c" * 51, "sale_price": "10.00"},
        {"name": "Bad\x00Name", "sale_price": "10.00"},
        {"name": "Valid", "code": "Bad\x00Code", "sale_price": "10.00"},
    ],
)
async def test_reject_blank_or_oversized_or_nul_byte_in_post_payload(
    catalog_auth_env: None,
    payload: dict[str, Any],
) -> None:
    """Scenario: Rejection of blank name, blank code, NUL bytes, or oversized strings."""
    cookies = _make_jwt_cookie(
        user_id=str(uuid.uuid4()),
        business_id=str(uuid.uuid4()),
        role="owner",
    )
    transport = httpx.ASGITransport(app=app)
    with _capture_sql_statements() as sql_log:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(CATALOG_PRODUCTS_URL, cookies=cookies, json=payload)

    _assert_uniform_error_response(response, 422, "VALIDATION_ERROR")
    assert not any("products" in stmt for stmt, _ in sql_log)


@pytest.mark.asyncio
async def test_reject_nul_byte_in_search_query_parameter(catalog_auth_env: None) -> None:
    """Scenario: Rejection of blank name, blank code, NUL bytes,
    or oversized strings (q with NUL).
    """
    cookies = _make_jwt_cookie(
        user_id=str(uuid.uuid4()),
        business_id=str(uuid.uuid4()),
        role="owner",
    )
    transport = httpx.ASGITransport(app=app)
    with _capture_sql_statements() as sql_log:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                CATALOG_PRODUCTS_URL,
                params={"q": "abc\x00def"},
                cookies=cookies,
            )

    _assert_uniform_error_response(response, 422, "VALIDATION_ERROR")
    assert not any("from products" in stmt for stmt, _ in sql_log)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "query_params",
    [
        {"limit": 0},
        {"limit": -1},
        {"limit": 201},
        {"offset": -1},
        {"q": "a" * 151},
    ],
)
async def test_reject_invalid_list_query_bounds(
    catalog_auth_env: None,
    query_params: dict[str, Any],
) -> None:
    """Scenario: Reject out-of-bounds limit (1..200), negative offset,
    and oversized search query (>150 chars) with 422 VALIDATION_ERROR.
    """
    cookies = _make_jwt_cookie(
        user_id=str(uuid.uuid4()),
        business_id=str(uuid.uuid4()),
        role="owner",
    )
    transport = httpx.ASGITransport(app=app)
    with _capture_sql_statements() as sql_log:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                CATALOG_PRODUCTS_URL,
                params=query_params,
                cookies=cookies,
            )

    _assert_uniform_error_response(response, 422, "VALIDATION_ERROR")
    assert not any("from products" in stmt for stmt, _ in sql_log)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "query_params",
    [
        {"limit": 1, "offset": 0},
        {"limit": 200, "offset": 0},
        {"q": "a" * 150},
    ],
)
async def test_accept_valid_list_query_boundary_values(
    catalog_auth_env: None,
    db_session: AsyncSession,
    query_params: dict[str, Any],
) -> None:
    """Scenario: Accept valid boundary values for limit (1, 200), offset (0),
    and search query length (150 chars).
    """
    user_id = str(uuid.uuid4())
    business_id = str(uuid.uuid4())

    async with db_session.begin():
        await _seed_business(db_session, business_id)
        await _seed_business_user(db_session, business_id, user_id, role="owner")

    cookies = _make_jwt_cookie(user_id=user_id, business_id=business_id, role="owner")
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                CATALOG_PRODUCTS_URL,
                params=query_params,
                cookies=cookies,
            )

        assert response.status_code == 200
        body = response.json()
        assert body["items"] == []
        assert body["total"] == 0
    finally:
        await _cleanup_businesses(db_session, [business_id])


@pytest.mark.asyncio
async def test_list_active_products_ordered_deterministically_with_negative_stock(
    catalog_auth_env: None,
    db_session: AsyncSession,
) -> None:
    """Scenario: List active products ordered deterministically by name and id."""
    user_id = str(uuid.uuid4())
    business_id = str(uuid.uuid4())
    id_low = "00000000-0000-0000-0000-000000000001"
    id_high = "00000000-0000-0000-0000-000000000002"

    async with db_session.begin():
        await _seed_business(db_session, business_id)
        await _seed_business_user(db_session, business_id, user_id, role="owner")
        await _seed_product(
            db_session,
            business_id=business_id,
            product_id=id_high,
            name="Bife",
            code=None,
            stock=Decimal("-1.50"),
        )
        await _seed_product(
            db_session,
            business_id=business_id,
            product_id=id_low,
            name="Bife",
            code="BIFE-1",
            stock=Decimal("3.00"),
        )
        await _seed_product(
            db_session,
            business_id=business_id,
            name="Azucar",
            code=None,
            stock=Decimal("0.00"),
        )

    cookies = _make_jwt_cookie(user_id=user_id, business_id=business_id, role="owner")
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(CATALOG_PRODUCTS_URL, cookies=cookies)

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 3
        assert body["limit"] == 50
        assert body["offset"] == 0
        items = body["items"]
        assert [(item["name"], item["id"]) for item in items] == [
            ("Azucar", items[0]["id"]),
            ("Bife", id_low),
            ("Bife", id_high),
        ]
        assert items[2]["stock"] == "-1.50"
        assert items[0]["code"] is None
    finally:
        await _cleanup_businesses(db_session, [business_id])


@pytest.mark.asyncio
async def test_search_products_case_insensitive_with_wildcard_escaping(
    catalog_auth_env: None,
    db_session: AsyncSession,
) -> None:
    """Scenario: Text search matches product name or code
    case-insensitively with SQL wildcard escaping.
    """
    user_id = str(uuid.uuid4())
    business_id = str(uuid.uuid4())

    async with db_session.begin():
        await _seed_business(db_session, business_id)
        await _seed_business_user(db_session, business_id, user_id, role="owner")
        await _seed_product(
            db_session,
            business_id=business_id,
            name="Descuento 10%",
            code="DSC-10",
        )
        await _seed_product(
            db_session,
            business_id=business_id,
            name="Descuento 100",
            code="DSC-100",
        )
        await _seed_product(
            db_session,
            business_id=business_id,
            name="Producto Normal",
            code="SKU_01",
        )
        await _seed_product(
            db_session,
            business_id=business_id,
            name="Otro Producto",
            code="SKU001",
        )
        await _seed_product(
            db_session,
            business_id=business_id,
            name="Cable 2\\3",
            code="SKU\\01",
        )
        await _seed_product(
            db_session,
            business_id=business_id,
            name="Cable 23",
            code="SKU01",
        )

    cookies = _make_jwt_cookie(user_id=user_id, business_id=business_id, role="owner")
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            pct_resp = await client.get(
                CATALOG_PRODUCTS_URL,
                params={"q": "10%"},
                cookies=cookies,
            )
            underscore_resp = await client.get(
                CATALOG_PRODUCTS_URL,
                params={"q": "sku_01"},
                cookies=cookies,
            )
            case_resp = await client.get(
                CATALOG_PRODUCTS_URL,
                params={"q": "DESCUENTO"},
                cookies=cookies,
            )
            backslash_name_resp = await client.get(
                CATALOG_PRODUCTS_URL,
                params={"q": "2\\3"},
                cookies=cookies,
            )
            backslash_code_resp = await client.get(
                CATALOG_PRODUCTS_URL,
                params={"q": "sku\\01"},
                cookies=cookies,
            )
            backslash_only_resp = await client.get(
                CATALOG_PRODUCTS_URL,
                params={"q": "\\"},
                cookies=cookies,
            )

        assert pct_resp.status_code == 200
        assert pct_resp.json()["total"] == 1
        assert [p["name"] for p in pct_resp.json()["items"]] == ["Descuento 10%"]

        assert underscore_resp.status_code == 200
        assert underscore_resp.json()["total"] == 1
        assert [p["code"] for p in underscore_resp.json()["items"]] == ["SKU_01"]

        assert case_resp.status_code == 200
        assert case_resp.json()["total"] == 2
        assert [p["name"] for p in case_resp.json()["items"]] == [
            "Descuento 10%",
            "Descuento 100",
        ]

        assert backslash_name_resp.status_code == 200
        assert backslash_name_resp.json()["total"] == 1
        assert [p["name"] for p in backslash_name_resp.json()["items"]] == ["Cable 2\\3"]

        assert backslash_code_resp.status_code == 200
        assert backslash_code_resp.json()["total"] == 1
        assert [p["code"] for p in backslash_code_resp.json()["items"]] == ["SKU\\01"]

        assert backslash_only_resp.status_code == 200
        assert backslash_only_resp.json()["total"] == 1
        assert [p["name"] for p in backslash_only_resp.json()["items"]] == ["Cable 2\\3"]
    finally:
        await _cleanup_businesses(db_session, [business_id])


@pytest.mark.asyncio
async def test_blank_search_query_returns_full_catalog_with_pagination(
    catalog_auth_env: None,
    db_session: AsyncSession,
) -> None:
    """Scenario: Empty or whitespace-only search query returns full
    active catalog and supports pagination.
    """
    user_id = str(uuid.uuid4())
    business_id = str(uuid.uuid4())

    async with db_session.begin():
        await _seed_business(db_session, business_id)
        await _seed_business_user(db_session, business_id, user_id, role="owner")
        for label in ["Prod A", "Prod B", "Prod C", "Prod D", "Prod E"]:
            await _seed_product(db_session, business_id=business_id, name=label)

    cookies = _make_jwt_cookie(user_id=user_id, business_id=business_id, role="owner")
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                CATALOG_PRODUCTS_URL,
                params={"q": "   ", "limit": 2, "offset": 2},
                cookies=cookies,
            )

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 5
        assert body["limit"] == 2
        assert body["offset"] == 2
        assert [item["name"] for item in body["items"]] == ["Prod C", "Prod D"]
    finally:
        await _cleanup_businesses(db_session, [business_id])


@pytest.mark.asyncio
async def test_inactive_products_hidden_by_default_and_revealed_when_requested(
    catalog_auth_env: None,
    db_session: AsyncSession,
) -> None:
    """Scenario: Inactive products hidden by default and revealed when include_inactive is true."""
    user_id = str(uuid.uuid4())
    business_id = str(uuid.uuid4())

    async with db_session.begin():
        await _seed_business(db_session, business_id)
        await _seed_business_user(db_session, business_id, user_id, role="owner")
        await _seed_product(db_session, business_id=business_id, name="Activo 1", is_active=True)
        await _seed_product(db_session, business_id=business_id, name="Activo 2", is_active=True)
        await _seed_product(db_session, business_id=business_id, name="Inactivo", is_active=False)

    cookies = _make_jwt_cookie(user_id=user_id, business_id=business_id, role="owner")
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            default_resp = await client.get(CATALOG_PRODUCTS_URL, cookies=cookies)
            all_resp = await client.get(
                CATALOG_PRODUCTS_URL,
                params={"include_inactive": "true"},
                cookies=cookies,
            )

        assert default_resp.status_code == 200
        assert default_resp.json()["total"] == 2
        assert [p["name"] for p in default_resp.json()["items"]] == ["Activo 1", "Activo 2"]

        assert all_resp.status_code == 200
        assert all_resp.json()["total"] == 3
        assert [p["name"] for p in all_resp.json()["items"]] == [
            "Activo 1",
            "Activo 2",
            "Inactivo",
        ]
    finally:
        await _cleanup_businesses(db_session, [business_id])


@pytest.mark.asyncio
async def test_unauthenticated_and_onboarding_pending_rejected(catalog_auth_env: None) -> None:
    """Scenario: Unauthenticated or onboarding-pending requests rejected with 401 and 403."""
    onboarding_cookies = _make_jwt_cookie(
        user_id=str(uuid.uuid4()),
        business_id=None,
        role=None,
    )
    transport = httpx.ASGITransport(app=app)
    with _capture_sql_statements() as sql_log:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            unauth_get = await client.get(CATALOG_PRODUCTS_URL)
            unauth_post = await client.post(
                CATALOG_PRODUCTS_URL,
                json={"name": "Item", "sale_price": "10.00"},
            )
            onb_get = await client.get(CATALOG_PRODUCTS_URL, cookies=onboarding_cookies)
            onb_post = await client.post(
                CATALOG_PRODUCTS_URL,
                cookies=onboarding_cookies,
                json={"name": "Item", "sale_price": "10.00"},
            )

    _assert_uniform_error_response(unauth_get, 401, "UNAUTHENTICATED")
    _assert_uniform_error_response(unauth_post, 401, "UNAUTHENTICATED")
    _assert_uniform_error_response(onb_get, 403, "ONBOARDING_REQUIRED")
    _assert_uniform_error_response(onb_post, 403, "ONBOARDING_REQUIRED")
    assert not any("products" in stmt for stmt, _ in sql_log)


@pytest.mark.asyncio
async def test_product_creation_restricted_to_owner_cashier_gets_403(
    catalog_auth_env: None,
    db_session: AsyncSession,
) -> None:
    """Scenario: Product creation restricted to owner role with 403 for cashier."""
    cashier_id = str(uuid.uuid4())
    business_id = str(uuid.uuid4())

    async with db_session.begin():
        await _seed_business(db_session, business_id)
        await _seed_business_user(db_session, business_id, cashier_id, role="cashier")

    cookies = _make_jwt_cookie(user_id=cashier_id, business_id=business_id, role="cashier")
    try:
        transport = httpx.ASGITransport(app=app)
        with _capture_sql_statements() as sql_log:
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    CATALOG_PRODUCTS_URL,
                    cookies=cookies,
                    json={"name": "No Permitido", "sale_price": "50.00"},
                )

        _assert_uniform_error_response(response, 403, "FORBIDDEN")
        assert not any("insert into products" in stmt for stmt, _ in sql_log)
    finally:
        await _cleanup_businesses(db_session, [business_id])


@pytest.mark.asyncio
async def test_listing_redacts_cost_price_for_cashier_and_exposes_to_owner(
    catalog_auth_env: None,
    db_session: AsyncSession,
) -> None:
    """Scenario: Listing redacts cost_price to null for cashier while exposing it to owner."""
    owner_id = str(uuid.uuid4())
    cashier_id = str(uuid.uuid4())
    business_id = str(uuid.uuid4())

    async with db_session.begin():
        await _seed_business(db_session, business_id)
        await _seed_business_user(db_session, business_id, owner_id, role="owner")
        await _seed_business_user(db_session, business_id, cashier_id, role="cashier")
        await _seed_product(
            db_session,
            business_id=business_id,
            name="Cafe",
            sale_price=Decimal("300.00"),
            cost_price=Decimal("150.00"),
        )

    owner_cookies = _make_jwt_cookie(user_id=owner_id, business_id=business_id, role="owner")
    cashier_cookies = _make_jwt_cookie(user_id=cashier_id, business_id=business_id, role="cashier")
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            cashier_resp = await client.get(CATALOG_PRODUCTS_URL, cookies=cashier_cookies)
            owner_resp = await client.get(CATALOG_PRODUCTS_URL, cookies=owner_cookies)

        assert cashier_resp.status_code == 200
        assert cashier_resp.json()["items"][0]["cost_price"] is None

        assert owner_resp.status_code == 200
        assert owner_resp.json()["items"][0]["cost_price"] == "150.00"
    finally:
        await _cleanup_businesses(db_session, [business_id])


@pytest.mark.asyncio
async def test_tenant_isolation_rls_and_ignore_body_business_id(
    catalog_auth_env: None,
    db_session: AsyncSession,
) -> None:
    """Scenario: Tenant isolation enforced via RLS prevents reading
    other business products and ignores body business_id.
    """
    business_a = str(uuid.uuid4())
    business_b = str(uuid.uuid4())
    owner_a = str(uuid.uuid4())

    async with db_session.begin():
        await _seed_business(db_session, business_a, name="Tenant A")
        await _seed_business(db_session, business_b, name="Tenant B")
        await _seed_business_user(db_session, business_a, owner_a, role="owner")
        await _seed_product(db_session, business_id=business_a, name="Producto A")
        await _seed_product(db_session, business_id=business_b, name="Producto B Secreto")

    cookies_a = _make_jwt_cookie(user_id=owner_a, business_id=business_a, role="owner")
    try:
        transport = httpx.ASGITransport(app=app)
        with _capture_sql_statements() as sql_log:
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                get_resp = await client.get(CATALOG_PRODUCTS_URL, cookies=cookies_a)
                post_resp = await client.post(
                    CATALOG_PRODUCTS_URL,
                    cookies=cookies_a,
                    json={
                        "business_id": business_b,
                        "name": "Creado En A",
                        "sale_price": "100.00",
                    },
                )

        assert get_resp.status_code == 200
        names = [item["name"] for item in get_resp.json()["items"]]
        assert names == ["Producto A"]
        assert "Producto B Secreto" not in names

        select_idx = next(i for i, (stmt, _) in enumerate(sql_log) if "from products" in stmt)
        assert any("set local role app_api" in stmt for stmt, _ in sql_log[:select_idx])
        assert any(
            "set_config" in stmt and "app.current_business_id" in stmt and business_a in params
            for stmt, params in sql_log[:select_idx]
        )

        assert post_resp.status_code == 201
        created_id = post_resp.json()["id"]
        async with db_session.begin():
            row = (
                (
                    await db_session.execute(
                        text("SELECT business_id FROM products WHERE id = :id"),
                        {"id": created_id},
                    )
                )
                .mappings()
                .one()
            )
            assert str(row["business_id"]) == business_a
    finally:
        await _cleanup_businesses(db_session, [business_a, business_b])


@pytest.mark.asyncio
async def test_openapi_documents_catalog_routes_and_schemas() -> None:
    """Scenario: Catalog routes and Decimal schemas documented in OpenAPI schema."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/openapi.json")

    assert response.status_code == 200
    spec = response.json()
    path_item = spec["paths"][CATALOG_PRODUCTS_URL]
    assert "get" in path_item
    assert "post" in path_item
    assert "catalog" in path_item["get"]["tags"]
    assert "catalog" in path_item["post"]["tags"]

    get_responses = set(path_item["get"]["responses"].keys())
    post_responses = set(path_item["post"]["responses"].keys())
    assert {"200", "401", "403", "422"}.issubset(get_responses)
    assert {"201", "401", "403", "409", "422"}.issubset(post_responses)

    schemas = spec["components"]["schemas"]
    assert "ErrorResponse" in schemas
    assert "ProductCreate" in schemas
    assert "ProductResponse" in schemas
    assert "ProductListResponse" in schemas

    product_response_props = schemas["ProductResponse"]["properties"]
    assert "sale_price" in product_response_props
    assert "cost_price" in product_response_props
    assert {"type": "null"} in product_response_props["cost_price"].get("anyOf", [])
    assert "stock" in product_response_props
    assert set(schemas["ProductListResponse"]["properties"].keys()) == {
        "items",
        "total",
        "limit",
        "offset",
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "huge_value",
    [
        "1e30",
        "1000000000000000000000000000",
        "100000000000000000000000000.00",
    ],
)
async def test_reject_huge_decimal_precision_without_500(
    catalog_auth_env: None,
    huge_value: str,
) -> None:
    """Scenario: Huge decimal strings (>28 digits) return 422 instead of 500 InvalidOperation."""
    cookies = _make_jwt_cookie(
        user_id=str(uuid.uuid4()),
        business_id=str(uuid.uuid4()),
        role="owner",
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            CATALOG_PRODUCTS_URL,
            json={"name": "Overflow", "sale_price": huge_value},
            cookies=cookies,
        )

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_offset", [2_147_483_648, 99_999_999_999_999_999_999])
async def test_reject_oversized_offset_without_500(
    catalog_auth_env: None,
    bad_offset: int,
) -> None:
    """Scenario: Oversized offset (> int32) returns 422 instead of 500 asyncpg DataError."""
    cookies = _make_jwt_cookie(
        user_id=str(uuid.uuid4()),
        business_id=str(uuid.uuid4()),
        role="owner",
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            CATALOG_PRODUCTS_URL,
            params={"offset": str(bad_offset)},
            cookies=cookies,
        )

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


# ==============================================================================
# PATCH /api/v1/catalog/products/{product_id} (Partial Product Update)
# ==============================================================================


@pytest.mark.asyncio
async def test_patch_product_partial_update_preserves_omitted_fields_including_negative_stock(
    catalog_auth_env: None,
    db_session: AsyncSession,
) -> None:
    """Scenario: Successful partial update of a subset of attributes preserves omitted fields."""
    user_id = str(uuid.uuid4())
    business_id = str(uuid.uuid4())

    async with db_session.begin():
        await _seed_business(db_session, business_id)
        await _seed_business_user(db_session, business_id, user_id, role="owner")
        product_id = await _seed_product(
            db_session,
            business_id=business_id,
            code="SKU-001",
            name="Yerba Mate",
            sale_price=Decimal("3000.00"),
            cost_price=Decimal("2000.00"),
            stock=Decimal("-1.50"),
            is_active=True,
        )
        initial_row = (
            (
                await db_session.execute(
                    text("SELECT created_at, updated_at FROM products WHERE id = :id"),
                    {"id": product_id},
                )
            )
            .mappings()
            .one()
        )
        initial_created_at = initial_row["created_at"]
        initial_updated_at = initial_row["updated_at"]

    cookies = _make_jwt_cookie(user_id=user_id, business_id=business_id, role="owner")
    try:
        transport = httpx.ASGITransport(app=app)
        with _capture_sql_statements() as sql_log:
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.patch(
                    f"{CATALOG_PRODUCTS_URL}/{product_id}",
                    cookies=cookies,
                    json={
                        "sale_price": "3500.50",
                        "cost_price": "2200.00",
                    },
                )

        assert response.status_code == 200
        body = response.json()
        assert body["id"] == product_id
        assert body["code"] == "SKU-001"
        assert body["name"] == "Yerba Mate"
        assert body["sale_price"] == "3500.50"
        assert body["cost_price"] == "2200.00"
        assert body["stock"] == "-1.50"
        assert body["is_active"] is True

        update_idx = next(i for i, (stmt, _) in enumerate(sql_log) if "update products" in stmt)
        assert any("set local role app_api" in stmt for stmt, _ in sql_log[:update_idx])
        assert any(
            "set_config" in stmt and "app.current_business_id" in stmt and business_id in params
            for stmt, params in sql_log[:update_idx]
        )

        async with db_session.begin():
            row = (
                (
                    await db_session.execute(
                        text(
                            """
                            SELECT business_id, code, name, sale_price, cost_price,
                                   stock, is_active, created_at, updated_at
                            FROM products WHERE id = :id
                            """
                        ),
                        {"id": product_id},
                    )
                )
                .mappings()
                .one()
            )
            assert str(row["business_id"]) == business_id
            assert row["code"] == "SKU-001"
            assert row["name"] == "Yerba Mate"
            assert row["sale_price"] == Decimal("3500.50")
            assert row["cost_price"] == Decimal("2200.00")
            assert row["stock"] == Decimal("-1.50")
            assert row["is_active"] is True
            assert row["created_at"] == initial_created_at
            assert row["updated_at"] > initial_updated_at
    finally:
        await _cleanup_businesses(db_session, [business_id])


@pytest.mark.asyncio
async def test_patch_product_all_editable_attributes_and_clear_code_to_null(
    catalog_auth_env: None,
    db_session: AsyncSession,
) -> None:
    """Scenario: Successful update of all editable attributes
    including clearing optional code to null.
    """
    user_id = str(uuid.uuid4())
    business_id = str(uuid.uuid4())

    async with db_session.begin():
        await _seed_business(db_session, business_id)
        await _seed_business_user(db_session, business_id, user_id, role="owner")
        await _seed_product(
            db_session,
            business_id=business_id,
            code=None,
            name="Otro Sin Codigo",
        )
        product_id = await _seed_product(
            db_session,
            business_id=business_id,
            code="SKU-CLEAR",
            name="Nombre Viejo",
            sale_price=Decimal("1000.00"),
            cost_price=Decimal("500.00"),
            stock=Decimal("5.00"),
        )

    cookies = _make_jwt_cookie(user_id=user_id, business_id=business_id, role="owner")
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.patch(
                f"{CATALOG_PRODUCTS_URL}/{product_id}",
                cookies=cookies,
                json={
                    "code": None,
                    "name": "  Nombre Nuevo Trim  ",
                    "sale_price": "1800.25",
                    "cost_price": "900.10",
                    "stock": "0.00",
                },
            )

        assert response.status_code == 200
        body = response.json()
        assert body["id"] == product_id
        assert body["code"] is None
        assert body["name"] == "Nombre Nuevo Trim"
        assert body["sale_price"] == "1800.25"
        assert body["cost_price"] == "900.10"
        assert body["stock"] == "0.00"
    finally:
        await _cleanup_businesses(db_session, [business_id])


@pytest.mark.asyncio
async def test_patch_product_keeping_own_code_or_matching_another_business_code_succeeds(
    catalog_auth_env: None,
    db_session: AsyncSession,
) -> None:
    """Scenario: Updating a product keeping its own code or matching a code
    from another business succeeds.
    """
    business_a = str(uuid.uuid4())
    business_b = str(uuid.uuid4())
    owner_a = str(uuid.uuid4())
    owner_b = str(uuid.uuid4())

    async with db_session.begin():
        await _seed_business(db_session, business_a, name="Business A")
        await _seed_business(db_session, business_b, name="Business B")
        await _seed_business_user(db_session, business_a, owner_a, role="owner")
        await _seed_business_user(db_session, business_b, owner_b, role="owner")
        p1_id = await _seed_product(
            db_session,
            business_id=business_a,
            code="ONLY-IN-A",
            name="Prod A1",
        )
        p2_id = await _seed_product(
            db_session,
            business_id=business_b,
            code="OLD-02",
            name="Prod B2",
        )

    cookies_a = _make_jwt_cookie(user_id=owner_a, business_id=business_a, role="owner")
    cookies_b = _make_jwt_cookie(user_id=owner_b, business_id=business_b, role="owner")
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp_a = await client.patch(
                f"{CATALOG_PRODUCTS_URL}/{p1_id}",
                cookies=cookies_a,
                json={"code": "ONLY-IN-A", "name": "Prod A1 Renombrado"},
            )
            resp_b = await client.patch(
                f"{CATALOG_PRODUCTS_URL}/{p2_id}",
                cookies=cookies_b,
                json={"code": "ONLY-IN-A"},
            )

        assert resp_a.status_code == 200
        assert resp_a.json()["code"] == "ONLY-IN-A"
        assert resp_a.json()["name"] == "Prod A1 Renombrado"

        assert resp_b.status_code == 200
        assert resp_b.json()["code"] == "ONLY-IN-A"
        assert resp_b.json()["name"] == "Prod B2"
    finally:
        await _cleanup_businesses(db_session, [business_a, business_b])


@pytest.mark.asyncio
async def test_patch_product_duplicate_code_same_business_returns_409_and_uses_savepoint(
    catalog_auth_env: None,
    db_session: AsyncSession,
) -> None:
    """Scenario: Updating code to an existing non-null code in the same business
    returns 409 Conflict and rolls back savepoint cleanly.
    """
    user_id = str(uuid.uuid4())
    business_id = str(uuid.uuid4())

    async with db_session.begin():
        await _seed_business(db_session, business_id)
        await _seed_business_user(db_session, business_id, user_id, role="owner")
        await _seed_product(
            db_session,
            business_id=business_id,
            code="SKU-001",
            name="Producto 1",
        )
        p2_id = await _seed_product(
            db_session,
            business_id=business_id,
            code="SKU-002",
            name="Producto 2",
            sale_price=Decimal("500.00"),
        )

    async def _override_get_tenant_db() -> AsyncGenerator[AsyncSession]:
        yield db_session

    cookies = _make_jwt_cookie(user_id=user_id, business_id=business_id, role="owner")
    app.dependency_overrides[get_tenant_db] = _override_get_tenant_db
    try:
        async with db_session.begin():
            await db_session.execute(text("SET LOCAL ROLE app_api"))
            await db_session.execute(
                text("SELECT set_config('app.current_business_id', :b_id, true)"),
                {"b_id": business_id},
            )
            await db_session.execute(
                text("SELECT set_config('app.current_user_id', :u_id, true)"),
                {"u_id": user_id},
            )

            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                dup_resp = await client.patch(
                    f"{CATALOG_PRODUCTS_URL}/{p2_id}",
                    cookies=cookies,
                    json={"code": "  SKU-001  ", "name": "Intento Duplicado"},
                )
                _assert_uniform_error_response(dup_resp, 409, "PRODUCT_CODE_ALREADY_EXISTS")

                # Verify outer transaction is not aborted and P2 attributes remain intact
                row = (
                    (
                        await db_session.execute(
                            text("SELECT code, name, sale_price FROM products WHERE id = :id"),
                            {"id": p2_id},
                        )
                    )
                    .mappings()
                    .one()
                )
                assert row["code"] == "SKU-002"
                assert row["name"] == "Producto 2"
                assert row["sale_price"] == Decimal("500.00")
    finally:
        app.dependency_overrides.pop(get_tenant_db, None)
        await _cleanup_businesses(db_session, [business_id])


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {"sale_price": 19.99},
        {"cost_price": 5.5},
        {"stock": 1.25},
        {"sale_price": True},
        {"cost_price": False},
        {"stock": True},
        {"sale_price": "NaN"},
        {"cost_price": "Infinity"},
        {"stock": "-Infinity"},
        {"sale_price": "12.345"},
        {"cost_price": "1.234"},
        {"stock": "0.001"},
        {"sale_price": "10000000000.00"},
        {"cost_price": "10000000000.00"},
        {"stock": "10000000000.00"},
        {"sale_price": "1e30"},
        {"sale_price": "1000000000000000000000000000"},
    ],
)
async def test_patch_rejects_float_bool_nonfinite_excessive_decimals_and_overflow(
    catalog_auth_env: None,
    payload: dict[str, Any],
) -> None:
    """Scenario: Rejection of float, bool, non-finite decimals, excessive decimal places,
    and numeric overflow on update.
    """
    cookies = _make_jwt_cookie(
        user_id=str(uuid.uuid4()),
        business_id=str(uuid.uuid4()),
        role="owner",
    )
    product_id = str(uuid.uuid4())
    transport = httpx.ASGITransport(app=app)
    with _capture_sql_statements() as sql_log:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.patch(
                f"{CATALOG_PRODUCTS_URL}/{product_id}",
                cookies=cookies,
                json=payload,
            )

    _assert_uniform_error_response(response, 422, "VALIDATION_ERROR")
    assert not any("update products" in stmt for stmt, _ in sql_log)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {"sale_price": "0.00"},
        {"sale_price": "-1.00"},
        {"cost_price": "-0.01"},
        {"stock": "-0.01"},
    ],
)
async def test_patch_rejects_non_positive_sale_price_negative_cost_or_negative_stock(
    catalog_auth_env: None,
    payload: dict[str, Any],
) -> None:
    """Scenario: Rejection of non-positive sale_price, negative cost_price,
    or negative stock on update.
    """
    cookies = _make_jwt_cookie(
        user_id=str(uuid.uuid4()),
        business_id=str(uuid.uuid4()),
        role="owner",
    )
    product_id = str(uuid.uuid4())
    transport = httpx.ASGITransport(app=app)
    with _capture_sql_statements() as sql_log:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.patch(
                f"{CATALOG_PRODUCTS_URL}/{product_id}",
                cookies=cookies,
                json=payload,
            )

    _assert_uniform_error_response(response, 422, "VALIDATION_ERROR")
    assert not any("update products" in stmt for stmt, _ in sql_log)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"business_id": str(uuid.uuid4())},
        {"name": None},
        {"sale_price": None},
        {"cost_price": None},
        {"stock": None},
    ],
)
async def test_patch_rejects_explicit_null_on_non_nullable_fields_or_empty_payload(
    catalog_auth_env: None,
    payload: dict[str, Any],
) -> None:
    """Scenario: Rejection of explicit null on non-nullable fields or empty update payload."""
    cookies = _make_jwt_cookie(
        user_id=str(uuid.uuid4()),
        business_id=str(uuid.uuid4()),
        role="owner",
    )
    product_id = str(uuid.uuid4())
    transport = httpx.ASGITransport(app=app)
    with _capture_sql_statements() as sql_log:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.patch(
                f"{CATALOG_PRODUCTS_URL}/{product_id}",
                cookies=cookies,
                json=payload,
            )

    _assert_uniform_error_response(response, 422, "VALIDATION_ERROR")
    assert not any("update products" in stmt for stmt, _ in sql_log)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "product_id_path,payload",
    [
        ("not-a-valid-uuid", {"name": "Valido"}),
        (str(uuid.uuid4()), {"name": ""}),
        (str(uuid.uuid4()), {"name": "   "}),
        (str(uuid.uuid4()), {"code": ""}),
        (str(uuid.uuid4()), {"code": "   "}),
        (str(uuid.uuid4()), {"name": "a" * 151}),
        (str(uuid.uuid4()), {"code": "c" * 51}),
        (str(uuid.uuid4()), {"name": "Bad\x00Name"}),
        (str(uuid.uuid4()), {"code": "Bad\x00Code"}),
    ],
)
async def test_patch_rejects_blank_oversized_nul_bytes_or_invalid_product_id_uuid(
    catalog_auth_env: None,
    product_id_path: str,
    payload: dict[str, Any],
) -> None:
    """Scenario: Rejection of blank strings, oversized strings, NUL bytes,
    or invalid product_id UUID.
    """
    cookies = _make_jwt_cookie(
        user_id=str(uuid.uuid4()),
        business_id=str(uuid.uuid4()),
        role="owner",
    )
    transport = httpx.ASGITransport(app=app)
    with _capture_sql_statements() as sql_log:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.patch(
                f"{CATALOG_PRODUCTS_URL}/{product_id_path}",
                cookies=cookies,
                json=payload,
            )

    _assert_uniform_error_response(response, 422, "VALIDATION_ERROR")
    assert not any("products" in stmt for stmt, _ in sql_log)


@pytest.mark.asyncio
async def test_patch_unauthenticated_and_onboarding_pending_rejected_with_401_and_403(
    catalog_auth_env: None,
) -> None:
    """Scenario: Unauthenticated or onboarding-pending update requests rejected with 401 and 403."""
    product_id = str(uuid.uuid4())
    onboarding_cookies = _make_jwt_cookie(
        user_id=str(uuid.uuid4()),
        business_id=None,
        role=None,
    )
    transport = httpx.ASGITransport(app=app)
    with _capture_sql_statements() as sql_log:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            unauth_resp = await client.patch(
                f"{CATALOG_PRODUCTS_URL}/{product_id}",
                json={"name": "Nuevo"},
            )
            onb_resp = await client.patch(
                f"{CATALOG_PRODUCTS_URL}/{product_id}",
                cookies=onboarding_cookies,
                json={"name": "Nuevo"},
            )

    _assert_uniform_error_response(unauth_resp, 401, "UNAUTHENTICATED")
    _assert_uniform_error_response(onb_resp, 403, "ONBOARDING_REQUIRED")
    assert not any("products" in stmt for stmt, _ in sql_log)


@pytest.mark.asyncio
async def test_patch_cashier_role_rejected_with_403_forbidden(
    catalog_auth_env: None,
    db_session: AsyncSession,
) -> None:
    """Scenario: Cashier role rejected with 403 Forbidden on product update."""
    cashier_id = str(uuid.uuid4())
    business_id = str(uuid.uuid4())

    async with db_session.begin():
        await _seed_business(db_session, business_id)
        await _seed_business_user(db_session, business_id, cashier_id, role="cashier")
        product_id = await _seed_product(
            db_session,
            business_id=business_id,
            name="Intocable Por Cajero",
            sale_price=Decimal("250.00"),
        )

    cookies = _make_jwt_cookie(user_id=cashier_id, business_id=business_id, role="cashier")
    try:
        transport = httpx.ASGITransport(app=app)
        with _capture_sql_statements() as sql_log:
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.patch(
                    f"{CATALOG_PRODUCTS_URL}/{product_id}",
                    cookies=cookies,
                    json={"sale_price": "300.00"},
                )

        _assert_uniform_error_response(response, 403, "FORBIDDEN")
        assert not any("update products" in stmt for stmt, _ in sql_log)
    finally:
        await _cleanup_businesses(db_session, [business_id])


@pytest.mark.asyncio
async def test_patch_non_existent_product_id_returns_404(
    catalog_auth_env: None,
    db_session: AsyncSession,
) -> None:
    """Scenario: Non-existent product_id returns 404 Not Found."""
    user_id = str(uuid.uuid4())
    business_id = str(uuid.uuid4())
    missing_product_id = str(uuid.uuid4())

    async with db_session.begin():
        await _seed_business(db_session, business_id)
        await _seed_business_user(db_session, business_id, user_id, role="owner")

    cookies = _make_jwt_cookie(user_id=user_id, business_id=business_id, role="owner")
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.patch(
                f"{CATALOG_PRODUCTS_URL}/{missing_product_id}",
                cookies=cookies,
                json={"name": "No Existe"},
            )

        _assert_uniform_error_response(response, 404, "PRODUCT_NOT_FOUND")
    finally:
        await _cleanup_businesses(db_session, [business_id])


@pytest.mark.asyncio
async def test_patch_cross_tenant_product_id_returns_404_and_leaves_target_unmodified(
    catalog_auth_env: None,
    db_session: AsyncSession,
) -> None:
    """Scenario: Cross-tenant product_id returns 404 Not Found
    without leaking existence or mutating data.
    """
    business_a = str(uuid.uuid4())
    business_b = str(uuid.uuid4())
    owner_a = str(uuid.uuid4())

    async with db_session.begin():
        await _seed_business(db_session, business_a, name="Tenant A")
        await _seed_business(db_session, business_b, name="Tenant B")
        await _seed_business_user(db_session, business_a, owner_a, role="owner")
        p_b_id = await _seed_product(
            db_session,
            business_id=business_b,
            code="B-SECRET",
            name="Producto B",
            sale_price=Decimal("700.00"),
        )

    cookies_a = _make_jwt_cookie(user_id=owner_a, business_id=business_a, role="owner")
    try:
        transport = httpx.ASGITransport(app=app)
        with _capture_sql_statements() as sql_log:
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.patch(
                    f"{CATALOG_PRODUCTS_URL}/{p_b_id}",
                    cookies=cookies_a,
                    json={"name": "Hackeado", "sale_price": "1.00"},
                )

        _assert_uniform_error_response(response, 404, "PRODUCT_NOT_FOUND")
        update_idx = next(i for i, (stmt, _) in enumerate(sql_log) if "update products" in stmt)
        assert any("set local role app_api" in stmt for stmt, _ in sql_log[:update_idx])
        assert any(
            "set_config" in stmt and "app.current_business_id" in stmt and business_a in params
            for stmt, params in sql_log[:update_idx]
        )

        async with db_session.begin():
            row = (
                (
                    await db_session.execute(
                        text(
                            "SELECT business_id, code, name, sale_price "
                            "FROM products WHERE id = :id"
                        ),
                        {"id": p_b_id},
                    )
                )
                .mappings()
                .one()
            )
            assert str(row["business_id"]) == business_b
            assert row["code"] == "B-SECRET"
            assert row["name"] == "Producto B"
            assert row["sale_price"] == Decimal("700.00")
    finally:
        await _cleanup_businesses(db_session, [business_a, business_b])


@pytest.mark.asyncio
async def test_patch_ignores_client_supplied_business_id_and_immutable_fields(
    catalog_auth_env: None,
    db_session: AsyncSession,
) -> None:
    """Scenario: Client-supplied business_id or immutable metadata fields in payload are ignored."""
    business_a = str(uuid.uuid4())
    business_b = str(uuid.uuid4())
    owner_a = str(uuid.uuid4())

    async with db_session.begin():
        await _seed_business(db_session, business_a, name="Tenant A")
        await _seed_business(db_session, business_b, name="Tenant B")
        await _seed_business_user(db_session, business_a, owner_a, role="owner")
        p_a_id = await _seed_product(
            db_session,
            business_id=business_a,
            name="Producto A",
            sale_price=Decimal("1000.00"),
        )

    cookies_a = _make_jwt_cookie(user_id=owner_a, business_id=business_a, role="owner")
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.patch(
                f"{CATALOG_PRODUCTS_URL}/{p_a_id}",
                cookies=cookies_a,
                json={
                    "business_id": business_b,
                    "id": str(uuid.uuid4()),
                    "sale_price": "1999.00",
                },
            )

        assert response.status_code == 200
        body = response.json()
        assert body["id"] == p_a_id
        assert body["sale_price"] == "1999.00"

        async with db_session.begin():
            row = (
                (
                    await db_session.execute(
                        text("SELECT business_id, sale_price FROM products WHERE id = :id"),
                        {"id": p_a_id},
                    )
                )
                .mappings()
                .one()
            )
            assert str(row["business_id"]) == business_a
            assert row["sale_price"] == Decimal("1999.00")
    finally:
        await _cleanup_businesses(db_session, [business_a, business_b])


@pytest.mark.asyncio
async def test_openapi_documents_patch_catalog_route_and_product_update_schema() -> None:
    """Scenario: PATCH catalog route and ProductUpdate schema documented
    in live and static OpenAPI contracts.
    """
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/openapi.json")

    assert response.status_code == 200
    spec = response.json()
    patch_path = f"{CATALOG_PRODUCTS_URL}/{{product_id}}"
    assert patch_path in spec["paths"]
    patch_op = spec["paths"][patch_path]["patch"]
    assert "catalog" in patch_op["tags"]

    param_names = {p["name"]: p for p in patch_op.get("parameters", [])}
    assert "product_id" in param_names
    assert param_names["product_id"]["in"] == "path"
    assert param_names["product_id"]["schema"].get("format") == "uuid"

    patch_responses = set(patch_op["responses"].keys())
    assert {"200", "401", "403", "404", "409", "422"}.issubset(patch_responses)

    schemas = spec["components"]["schemas"]
    assert "ProductUpdate" in schemas
    update_props = schemas["ProductUpdate"]["properties"]
    assert {"code", "name", "sale_price", "cost_price", "stock"}.issubset(set(update_props.keys()))
