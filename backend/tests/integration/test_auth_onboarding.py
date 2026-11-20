import asyncio
import importlib.util
import time
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

import httpx
import jwt
import pytest
from fastapi import Depends, FastAPI
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.main import app

pytestmark = pytest.mark.auth

TEST_SUPABASE_URL = "https://supabase.test.local"
TEST_SUPABASE_ANON_KEY = "test-supabase-anon-key"
TEST_JWT_SECRET = "test-jwt-secret-key-for-integration-tests-32b"


@pytest.fixture
def auth_env(monkeypatch: pytest.MonkeyPatch):
    from app.core.rate_limit import login_rate_limiter

    login_rate_limiter.reset()
    monkeypatch.setenv("SUPABASE_URL", TEST_SUPABASE_URL)
    monkeypatch.setenv("SUPABASE_ANON_KEY", TEST_SUPABASE_ANON_KEY)
    monkeypatch.setenv("JWT_SECRET_KEY", TEST_JWT_SECRET)
    monkeypatch.setenv("COOKIE_SECURE", "false")
    if hasattr(get_settings, "cache_clear"):
        get_settings.cache_clear()
    yield
    login_rate_limiter.reset()
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
        "iat": now,
        "exp": now + exp_offset_seconds,
    }
    token = jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")
    return {"access_token": token}


def _patch_supabase_auth(
    monkeypatch: pytest.MonkeyPatch,
    handler: Callable[[httpx.Request], httpx.Response],
) -> list[httpx.Request]:
    captured_requests: list[httpx.Request] = []
    original_handle = httpx.AsyncHTTPTransport.handle_async_request

    async def _mock_handle(
        self: httpx.AsyncHTTPTransport,
        request: httpx.Request,
    ) -> httpx.Response:
        if str(request.url).startswith(TEST_SUPABASE_URL):
            captured_requests.append(request)
            return handler(request)
        return await original_handle(self, request)

    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", _mock_handle)
    return captured_requests


async def _seed_business(
    db_session: AsyncSession,
    business_id: str,
    name: str = "Kiosco Test",
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


@pytest.mark.asyncio
async def test_login_success_with_existing_business(
    auth_env: None,
    monkeypatch: pytest.MonkeyPatch,
    db_session: AsyncSession,
) -> None:
    """Scenario: Successful login with existing business."""
    monkeypatch.setenv("COOKIE_SECURE", "true")
    if hasattr(get_settings, "cache_clear"):
        get_settings.cache_clear()

    user_id = str(uuid.uuid4())
    business_id = str(uuid.uuid4())
    email = "owner@kiosco.test"

    async with db_session.begin():
        await _seed_business(db_session, business_id, name="Kiosco Central")
        await _seed_business_user(db_session, business_id, user_id, role="owner")

    def _supabase_ok(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"user": {"id": user_id, "email": email}, "access_token": "sb-access"},
        )

    captured = _patch_supabase_auth(monkeypatch, _supabase_ok)

    try:
        transport = httpx.ASGITransport(app=app)
        with _capture_sql_statements() as sql_log:
            async with httpx.AsyncClient(transport=transport, base_url="https://test") as client:
                response = await client.post(
                    "/api/v1/auth/login",
                    json={"email": email, "password": "valid-password"},
                )

        assert response.status_code == 200
        bu_select_idx = next(
            i for i, (stmt, _) in enumerate(sql_log) if "from business_users" in stmt
        )
        biz_select_idx = next(i for i, (stmt, _) in enumerate(sql_log) if "from businesses" in stmt)
        assert any("set local role app_api" in stmt for stmt, _ in sql_log[:bu_select_idx])
        assert any(
            "set_config" in stmt and "app.current_user_id" in stmt and user_id in params
            for stmt, params in sql_log[:bu_select_idx]
        )
        assert any(
            "set_config" in stmt and "app.current_business_id" in stmt and business_id in params
            for stmt, params in sql_log[:biz_select_idx]
        )
        body = response.json()
        assert body["requires_onboarding"] is False
        assert body["user"] == {"id": user_id, "email": email}
        assert body["business"] == {
            "id": business_id,
            "name": "Kiosco Central",
            "country": "AR",
            "timezone": "America/Argentina/Buenos_Aires",
            "role": "owner",
        }

        assert len(captured) == 1
        assert captured[0].headers.get("apikey") == TEST_SUPABASE_ANON_KEY

        set_cookies = [v.lower() for v in response.headers.get_list("set-cookie")]
        assert any("access_token=" in c for c in set_cookies)
        cookie_header = next(c for c in set_cookies if "access_token=" in c)
        assert "httponly" in cookie_header
        assert "samesite=strict" in cookie_header
        assert "secure" in cookie_header

        token = response.cookies.get("access_token")
        assert token is not None
        claims = jwt.decode(token, TEST_JWT_SECRET, algorithms=["HS256"])
        assert claims["sub"] == user_id
        assert claims["email"] == email
        assert claims["business_id"] == business_id
        assert claims["role"] == "owner"
        assert claims["exp"] > claims["iat"]
    finally:
        await _cleanup_businesses(db_session, [business_id])


@pytest.mark.asyncio
async def test_login_success_requiring_onboarding(
    auth_env: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scenario: Successful login requiring onboarding."""
    user_id = str(uuid.uuid4())
    email = "newuser@kiosco.test"

    def _supabase_ok(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"user": {"id": user_id, "email": email}, "access_token": "sb-access"},
        )

    _patch_supabase_auth(monkeypatch, _supabase_ok)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "valid-password"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["requires_onboarding"] is True
    assert body["business"] is None
    assert body["user"] == {"id": user_id, "email": email}

    token = response.cookies.get("access_token")
    assert token is not None
    claims = jwt.decode(token, TEST_JWT_SECRET, algorithms=["HS256"])
    assert claims["sub"] == user_id
    assert claims["business_id"] is None
    assert claims["role"] is None


@pytest.mark.asyncio
async def test_login_invalid_credentials_returns_401_without_cookie(
    auth_env: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scenario: Invalid credentials."""

    def _supabase_fail(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={"error": "invalid_grant", "error_description": "Invalid login credentials"},
        )

    _patch_supabase_auth(monkeypatch, _supabase_fail)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "wrong@kiosco.test", "password": "bad-password"},
        )

    assert response.status_code == 401
    body = response.json()
    assert "code" in body
    assert "message" in body
    assert "details" in body
    assert response.cookies.get("access_token") is None


@pytest.mark.asyncio
async def test_onboarding_success_with_country_timezone_resolution(
    auth_env: None,
    db_session: AsyncSession,
) -> None:
    """Scenario: Successful business onboarding with country timezone resolution."""
    user_id = str(uuid.uuid4())
    email = "onboard@kiosco.test"
    created_business_id: str | None = None

    try:
        transport = httpx.ASGITransport(app=app)
        with _capture_sql_statements() as sql_log:
            async with httpx.AsyncClient(
                transport=transport,
                base_url="http://test",
                cookies=_make_jwt_cookie(user_id=user_id, email=email),
            ) as client:
                response = await client.post(
                    "/api/v1/auth/onboarding",
                    json={"name": "Kiosco Sol", "country": "AR"},
                )

        assert response.status_code == 201
        body = response.json()
        created_business_id = body["id"]

        biz_insert_idx = next(
            i for i, (stmt, _) in enumerate(sql_log) if "insert into businesses" in stmt
        )
        assert any("set local role app_api" in stmt for stmt, _ in sql_log[:biz_insert_idx])
        assert any(
            "set_config" in stmt and "app.current_user_id" in stmt and user_id in params
            for stmt, params in sql_log[:biz_insert_idx]
        )
        assert any(
            "set_config" in stmt
            and "app.current_business_id" in stmt
            and created_business_id in params
            for stmt, params in sql_log[:biz_insert_idx]
        )
        assert uuid.UUID(created_business_id)
        assert body["name"] == "Kiosco Sol"
        assert body["country"] == "AR"
        assert body["timezone"] == "America/Argentina/Buenos_Aires"
        assert body["role"] == "owner"
        assert "created_at" in body

        refreshed_token = response.cookies.get("access_token")
        assert refreshed_token is not None
        claims = jwt.decode(refreshed_token, TEST_JWT_SECRET, algorithms=["HS256"])
        assert claims["sub"] == user_id
        assert claims["business_id"] == created_business_id
        assert claims["role"] == "owner"

        async with db_session.begin():
            await db_session.execute(text(f"SET LOCAL app.current_user_id = '{user_id}';"))
            await db_session.execute(
                text(f"SET LOCAL app.current_business_id = '{created_business_id}';")
            )
            bu_row = (
                await db_session.execute(
                    text("SELECT business_id, role FROM business_users WHERE user_id = :u"),
                    {"u": user_id},
                )
            ).one()
            assert str(bu_row[0]) == created_business_id
            assert bu_row[1] == "owner"
    finally:
        if created_business_id:
            await _cleanup_businesses(db_session, [created_business_id])


@pytest.mark.asyncio
async def test_onboarding_success_with_explicit_valid_iana_timezone(
    auth_env: None,
    db_session: AsyncSession,
) -> None:
    """Scenario: Successful business onboarding with explicit valid IANA timezone."""
    user_id = str(uuid.uuid4())
    created_business_id: str | None = None

    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
            cookies=_make_jwt_cookie(user_id=user_id),
        ) as client:
            response = await client.post(
                "/api/v1/auth/onboarding",
                json={
                    "name": "Almacen Cordoba",
                    "country": "AR",
                    "timezone": "America/Argentina/Cordoba",
                },
            )

        assert response.status_code == 201
        body = response.json()
        created_business_id = body["id"]
        assert body["timezone"] == "America/Argentina/Cordoba"
        assert body["role"] == "owner"
        assert response.cookies.get("access_token") is not None
    finally:
        if created_business_id:
            await _cleanup_businesses(db_session, [created_business_id])


@pytest.mark.asyncio
async def test_onboarding_unauthenticated_returns_401(auth_env: None) -> None:
    """Scenario: Unauthenticated onboarding attempt."""
    transport = httpx.ASGITransport(app=app)
    payload = {"name": "Kiosco Sin Auth", "country": "AR"}

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res_missing = await client.post("/api/v1/auth/onboarding", json=payload)
        assert res_missing.status_code == 401

        res_malformed = await client.post(
            "/api/v1/auth/onboarding",
            json=payload,
            cookies={"access_token": "not.a.valid.jwt"},
        )
        assert res_malformed.status_code == 401

        expired_cookie = _make_jwt_cookie(
            user_id=str(uuid.uuid4()),
            exp_offset_seconds=-60,
        )
        res_expired = await client.post(
            "/api/v1/auth/onboarding",
            json=payload,
            cookies=expired_cookie,
        )
        assert res_expired.status_code == 401

        wrong_sig_token = jwt.encode(
            {
                "sub": str(uuid.uuid4()),
                "email": "attacker@example.com",
                "business_id": None,
                "role": None,
                "iat": int(time.time()),
                "exp": int(time.time()) + 900,
            },
            "wrong-jwt-secret-key-not-matching-server",
            algorithm="HS256",
        )
        res_wrong_sig = await client.post(
            "/api/v1/auth/onboarding",
            json=payload,
            cookies={"access_token": wrong_sig_token},
        )
        assert res_wrong_sig.status_code == 401


@pytest.mark.asyncio
async def test_onboarding_duplicate_business_returns_409(
    auth_env: None,
    db_session: AsyncSession,
) -> None:
    """Scenario: Duplicate business creation attempt."""
    user_id = str(uuid.uuid4())
    existing_business_id = str(uuid.uuid4())

    async with db_session.begin():
        await _seed_business(db_session, existing_business_id, name="Negocio Existente")
        await _seed_business_user(db_session, existing_business_id, user_id, role="owner")

    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
            cookies=_make_jwt_cookie(user_id=user_id, business_id=None),
        ) as client:
            response = await client.post(
                "/api/v1/auth/onboarding",
                json={"name": "Segundo Negocio", "country": "AR"},
            )

        assert response.status_code == 409
        assert response.json()["code"] == "BUSINESS_ALREADY_EXISTS"

        async with db_session.begin():
            await db_session.execute(text(f"SET LOCAL app.current_user_id = '{user_id}';"))
            await db_session.execute(
                text(f"SET LOCAL app.current_business_id = '{existing_business_id}';")
            )
            count_bu = (
                await db_session.execute(
                    text("SELECT count(*) FROM business_users WHERE user_id = :u"),
                    {"u": user_id},
                )
            ).scalar_one()
            assert count_bu == 1
    finally:
        await _cleanup_businesses(db_session, [existing_business_id])


@pytest.mark.asyncio
async def test_onboarding_concurrent_requests_enforce_single_business_no_orphans(
    auth_env: None,
    db_session: AsyncSession,
) -> None:
    """Scenario: Concurrent onboarding requests enforce single business per user."""
    user_id = str(uuid.uuid4())
    created_ids: list[str] = []
    marker_prefix = f"Concurrent-{user_id[:8]}"

    try:
        transport = httpx.ASGITransport(app=app)
        cookies = _make_jwt_cookie(user_id=user_id)

        async def _send_onboarding(suffix: str) -> httpx.Response:
            async with httpx.AsyncClient(
                transport=transport,
                base_url="http://test",
                cookies=cookies,
            ) as client:
                return await client.post(
                    "/api/v1/auth/onboarding",
                    json={"name": f"{marker_prefix}-{suffix}", "country": "AR"},
                )

        res_a, res_b = await asyncio.gather(_send_onboarding("A"), _send_onboarding("B"))
        statuses = sorted([res_a.status_code, res_b.status_code])
        assert statuses == [201, 409]

        winner = res_a if res_a.status_code == 201 else res_b
        created_ids.append(winner.json()["id"])

        async with db_session.begin():
            winner_id = winner.json()["id"]
            await db_session.execute(text(f"SET LOCAL app.current_user_id = '{user_id}';"))
            await db_session.execute(text(f"SET LOCAL app.current_business_id = '{winner_id}';"))
            bu_count = (
                await db_session.execute(
                    text("SELECT count(*) FROM business_users WHERE user_id = :u"),
                    {"u": user_id},
                )
            ).scalar_one()
            assert bu_count == 1

            biz_count = (
                await db_session.execute(
                    text("SELECT count(*) FROM businesses WHERE name LIKE :prefix"),
                    {"prefix": f"{marker_prefix}%"},
                )
            ).scalar_one()
            assert biz_count == 1
    finally:
        await _cleanup_businesses(db_session, created_ids)


@pytest.mark.asyncio
async def test_rls_login_membership_lookup_no_deadlock_and_isolates_users(
    auth_env: None,
    monkeypatch: pytest.MonkeyPatch,
    db_session: AsyncSession,
) -> None:
    """Scenario: Login membership lookup uses app current user id without deadlock."""
    user_a = str(uuid.uuid4())
    user_b = str(uuid.uuid4())
    biz_a = str(uuid.uuid4())
    biz_b = str(uuid.uuid4())

    async with db_session.begin():
        await _seed_business(db_session, biz_a, name="Comercio A")
        await _seed_business(db_session, biz_b, name="Comercio B")
        await _seed_business_user(db_session, biz_a, user_a, role="owner")
        await _seed_business_user(db_session, biz_b, user_b, role="owner")

    def _supabase_user_a(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"user": {"id": user_a, "email": "a@kiosco.test"}, "access_token": "sb-a"},
        )

    _patch_supabase_auth(monkeypatch, _supabase_user_a)

    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/login",
                json={"email": "a@kiosco.test", "password": "secret"},
            )

        assert response.status_code == 200
        body = response.json()
        assert body["requires_onboarding"] is False
        assert body["business"]["id"] == biz_a
    finally:
        await _cleanup_businesses(db_session, [biz_a, biz_b])


@pytest.mark.asyncio
async def test_rls_valid_tenant_context_and_cross_tenant_isolation(
    auth_env: None,
    db_session: AsyncSession,
) -> None:
    """Scenarios: Valid tenant context set on transactional session.

    Also covers: Cross-tenant database isolation enforced under app_api.
    """
    if importlib.util.find_spec("app.core.db") is None:
        pytest.fail("Tenant DB dependency app.core.db.get_tenant_db is not implemented yet")
    from app.core.db import get_tenant_db

    user_a = str(uuid.uuid4())
    user_b = str(uuid.uuid4())
    biz_a = str(uuid.uuid4())
    biz_b = str(uuid.uuid4())

    async with db_session.begin():
        await _seed_business(db_session, biz_a, name="Tenant A")
        await _seed_business(db_session, biz_b, name="Tenant B")
        await _seed_business_user(db_session, biz_a, user_a, role="owner")
        await _seed_business_user(db_session, biz_b, user_b, role="owner")

    probe_app = FastAPI()

    @probe_app.get("/_test/tenant-probe")
    async def _tenant_probe(db: AsyncSession = Depends(get_tenant_db)) -> dict[str, Any]:
        ctx_row = (
            await db.execute(
                text(
                    "SELECT current_user, "
                    "current_setting('app.current_user_id', true), "
                    "current_setting('app.current_business_id', true)"
                )
            )
        ).one()
        visible_businesses = [
            str(r[0]) for r in (await db.execute(text("SELECT id FROM businesses"))).fetchall()
        ]
        cross_business = (
            await db.execute(
                text("SELECT id FROM businesses WHERE id = :target"),
                {"target": biz_b},
            )
        ).fetchall()
        cross_members = (
            await db.execute(
                text("SELECT user_id FROM business_users WHERE business_id = :target"),
                {"target": biz_b},
            )
        ).fetchall()
        return {
            "role": ctx_row[0],
            "user_id": ctx_row[1],
            "business_id": ctx_row[2],
            "visible_businesses": visible_businesses,
            "cross_business_count": len(cross_business),
            "cross_members_count": len(cross_members),
        }

    try:
        transport = httpx.ASGITransport(app=probe_app)
        cookies = _make_jwt_cookie(user_id=user_a, business_id=biz_a, role="owner")
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
            cookies=cookies,
        ) as client:
            response = await client.get("/_test/tenant-probe")

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "app_api"
        assert data["user_id"] == user_a
        assert data["business_id"] == biz_a
        assert data["visible_businesses"] == [biz_a]
        assert data["cross_business_count"] == 0
        assert data["cross_members_count"] == 0
    finally:
        await _cleanup_businesses(db_session, [biz_a, biz_b])


@pytest.mark.asyncio
async def test_rls_request_lacking_business_context_blocked(auth_env: None) -> None:
    """Scenario: Request lacking business context blocked from tenant resources."""
    if importlib.util.find_spec("app.core.db") is None:
        pytest.fail("Tenant DB dependency app.core.db.get_tenant_db is not implemented yet")
    from app.core.db import get_tenant_db

    probe_app = FastAPI()

    @probe_app.get("/_test/tenant-protected")
    async def _tenant_protected(db: AsyncSession = Depends(get_tenant_db)) -> dict[str, str]:
        return {"status": "ok"}

    transport = httpx.ASGITransport(app=probe_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        unauth_res = await client.get("/_test/tenant-protected")
        assert unauth_res.status_code == 401

        pending_onboarding_cookie = _make_jwt_cookie(
            user_id=str(uuid.uuid4()),
            business_id=None,
            role=None,
        )
        no_biz_res = await client.get(
            "/_test/tenant-protected",
            cookies=pending_onboarding_cookie,
        )
        assert no_biz_res.status_code == 403


@pytest.mark.asyncio
async def test_onboarding_with_existing_business_in_jwt_returns_409_without_insert(
    auth_env: None,
    db_session: AsyncSession,
) -> None:
    """Guard: JWT already carrying business_id is rejected with 409 before DB insert."""
    user_id = str(uuid.uuid4())
    jwt_business_id = str(uuid.uuid4())
    accidentally_created_id: str | None = None

    try:
        transport = httpx.ASGITransport(app=app)
        with _capture_sql_statements() as sql_log:
            async with httpx.AsyncClient(
                transport=transport,
                base_url="http://test",
                cookies=_make_jwt_cookie(
                    user_id=user_id,
                    business_id=jwt_business_id,
                    role="owner",
                ),
            ) as client:
                response = await client.post(
                    "/api/v1/auth/onboarding",
                    json={"name": "Negocio Duplicado JWT", "country": "AR"},
                )

        if response.status_code == 201:
            accidentally_created_id = response.json().get("id")

        assert response.status_code == 409
        assert response.json()["code"] == "BUSINESS_ALREADY_EXISTS"
        assert not any("insert into businesses" in stmt for stmt, _ in sql_log)
    finally:
        if accidentally_created_id:
            await _cleanup_businesses(db_session, [accidentally_created_id])


@pytest.mark.asyncio
async def test_rls_user_db_context_and_isolation(
    auth_env: None,
    db_session: AsyncSession,
) -> None:
    """Scenario: get_user_db sets app_api + app.current_user_id and isolates business_users."""
    if importlib.util.find_spec("app.core.db") is None:
        pytest.fail("User DB dependency app.core.db.get_user_db is not implemented yet")
    from app.core.db import get_user_db

    user_a = str(uuid.uuid4())
    user_b = str(uuid.uuid4())
    biz_a = str(uuid.uuid4())
    biz_b = str(uuid.uuid4())

    async with db_session.begin():
        await _seed_business(db_session, biz_a, name="Negocio User A")
        await _seed_business(db_session, biz_b, name="Negocio User B")
        await _seed_business_user(db_session, biz_a, user_a, role="owner")
        await _seed_business_user(db_session, biz_b, user_b, role="owner")

    probe_app = FastAPI()

    @probe_app.get("/_test/user-probe")
    async def _user_probe(db: AsyncSession = Depends(get_user_db)) -> dict[str, Any]:
        ctx_row = (
            await db.execute(
                text(
                    "SELECT current_user, "
                    "current_setting('app.current_user_id', true), "
                    "current_setting('app.current_business_id', true)"
                )
            )
        ).one()
        memberships = [
            [str(r[0]), str(r[1])]
            for r in (
                await db.execute(text("SELECT business_id, user_id FROM business_users"))
            ).fetchall()
        ]
        return {
            "role": ctx_row[0],
            "user_id": ctx_row[1],
            "business_id": ctx_row[2],
            "memberships": memberships,
        }

    try:
        transport = httpx.ASGITransport(app=probe_app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            unauth_res = await client.get("/_test/user-probe")
            assert unauth_res.status_code == 401

            auth_res = await client.get(
                "/_test/user-probe",
                cookies=_make_jwt_cookie(user_id=user_a, business_id=None, role=None),
            )

        assert auth_res.status_code == 200
        data = auth_res.json()
        assert data["role"] == "app_api"
        assert data["user_id"] == user_a
        assert data["memberships"] == [[biz_a, user_a]]
    finally:
        await _cleanup_businesses(db_session, [biz_a, biz_b])


@pytest.mark.asyncio
async def test_login_maps_supabase_429_5xx_and_timeout_without_masking_as_401(
    auth_env: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = httpx.ASGITransport(app=app)

    # 1. Supabase 429 -> 429 UPSTREAM_RATE_LIMITED
    _patch_supabase_auth(
        monkeypatch,
        lambda _req: httpx.Response(status_code=429, json={"error": "rate_limit"}),
    )
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res_429 = await client.post(
            "/api/v1/auth/login",
            json={"email": "rl-429@example.com", "password": "secret"},
        )
    assert res_429.status_code == 429
    assert res_429.json()["code"] == "UPSTREAM_RATE_LIMITED"
    assert "access_token" not in res_429.cookies

    # 2. Supabase 503 -> 502/503 AUTH_UPSTREAM_UNAVAILABLE
    _patch_supabase_auth(
        monkeypatch,
        lambda _req: httpx.Response(status_code=503, json={"error": "unavailable"}),
    )
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res_503 = await client.post(
            "/api/v1/auth/login",
            json={"email": "rl-503@example.com", "password": "secret"},
        )
    assert res_503.status_code in (502, 503)
    assert res_503.json()["code"] == "AUTH_UPSTREAM_UNAVAILABLE"

    # 3. httpx.ReadTimeout -> 503 AUTH_UPSTREAM_TIMEOUT
    def _raise_timeout(_req: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("Supabase timed out")

    _patch_supabase_auth(monkeypatch, _raise_timeout)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res_timeout = await client.post(
            "/api/v1/auth/login",
            json={"email": "rl-timeout@example.com", "password": "secret"},
        )
    assert res_timeout.status_code == 503
    assert res_timeout.json()["code"] == "AUTH_UPSTREAM_TIMEOUT"


@pytest.mark.asyncio
async def test_login_rate_limiter_blocks_excessive_requests_per_email(
    auth_env: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOGIN_RATE_LIMIT_EMAIL_MAX", "2")
    if hasattr(get_settings, "cache_clear"):
        get_settings.cache_clear()

    calls = _patch_supabase_auth(
        monkeypatch,
        lambda _req: httpx.Response(status_code=400, json={"error": "invalid_grant"}),
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        r1 = await client.post(
            "/api/v1/auth/login",
            json={"email": "bruteforce@example.com", "password": "wrong"},
        )
        r2 = await client.post(
            "/api/v1/auth/login",
            json={"email": "bruteforce@example.com", "password": "wrong"},
        )
        r3 = await client.post(
            "/api/v1/auth/login",
            json={"email": "bruteforce@example.com", "password": "wrong"},
        )

    assert r1.status_code == 401
    assert r2.status_code == 401
    assert r3.status_code == 429
    assert r3.json()["code"] == "RATE_LIMIT_EXCEEDED"
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_error_responses_use_unified_error_response_format(auth_env: None) -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        unauth_res = await client.post(
            "/api/v1/auth/onboarding",
            json={"name": "Kiosco", "country": "AR"},
        )
        invalid_res = await client.post(
            "/api/v1/auth/login",
            json={"email": "not-an-email", "password": ""},
        )

    assert unauth_res.status_code == 401
    unauth_body = unauth_res.json()
    assert set(unauth_body.keys()) == {"code", "message", "details"}
    assert unauth_body["code"] == "UNAUTHENTICATED"

    assert invalid_res.status_code == 422
    invalid_body = invalid_res.json()
    assert set(invalid_body.keys()) == {"code", "message", "details"}
    assert invalid_body["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_set_rls_user_context_clears_residual_business_id(db_session: AsyncSession) -> None:
    from app.core.db import set_rls_business_context, set_rls_user_context

    u1 = uuid.uuid4()
    b1 = uuid.uuid4()
    async with db_session.begin() as tx:
        try:
            await set_rls_business_context(db_session, b1)
            await set_rls_user_context(db_session, u1)
            biz_guc = (
                await db_session.execute(
                    text("SELECT current_setting('app.current_business_id', true)")
                )
            ).scalar_one()
            assert biz_guc == ""
        finally:
            await tx.rollback()


@pytest.mark.asyncio
async def test_auth_me_returns_session_and_rejects_unauthenticated(
    auth_env: None,
    db_session: AsyncSession,
) -> None:
    user_id = str(uuid.uuid4())
    biz_id = str(uuid.uuid4())
    user_no_biz = str(uuid.uuid4())

    async with db_session.begin():
        await _seed_business(db_session, biz_id, name="Panadería Sol")
        await _seed_business_user(db_session, biz_id, user_id, role="owner")

    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            unauth = await client.get("/api/v1/auth/me")
            assert unauth.status_code == 401
            assert unauth.json()["code"] == "UNAUTHENTICATED"

            with_biz = await client.get(
                "/api/v1/auth/me",
                cookies=_make_jwt_cookie(
                    user_id=user_id,
                    email="pan@example.com",
                    business_id=biz_id,
                    role="owner",
                ),
            )
            assert with_biz.status_code == 200
            body_biz = with_biz.json()
            assert body_biz["user"] == {"id": user_id, "email": "pan@example.com"}
            assert body_biz["requires_onboarding"] is False
            assert body_biz["business"]["id"] == biz_id
            assert body_biz["business"]["name"] == "Panadería Sol"

            without_biz = await client.get(
                "/api/v1/auth/me",
                cookies=_make_jwt_cookie(user_id=user_no_biz, email="nuevo@example.com"),
            )
            assert without_biz.status_code == 200
            body_no_biz = without_biz.json()
            assert body_no_biz["requires_onboarding"] is True
            assert body_no_biz["business"] is None
    finally:
        await _cleanup_businesses(db_session, [biz_id])


@pytest.mark.asyncio
async def test_auth_logout_clears_access_and_refresh_cookies(auth_env: None) -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/v1/auth/logout")

    assert res.status_code == 204
    set_cookies = res.headers.get_list("set-cookie")
    assert any("access_token=" in header and "Max-Age=0" in header for header in set_cookies)
    assert any("refresh_token=" in header and "Max-Age=0" in header for header in set_cookies)
    assert all("HttpOnly" in header and "SameSite=strict" in header for header in set_cookies)


@pytest.mark.asyncio
async def test_auth_refresh_renews_tokens_and_rejects_invalid_or_access_token(
    auth_env: None,
    monkeypatch: pytest.MonkeyPatch,
    db_session: AsyncSession,
) -> None:
    user_id = str(uuid.uuid4())
    biz_id = str(uuid.uuid4())

    async with db_session.begin():
        await _seed_business(db_session, biz_id, name="Kiosco Refresh")
        await _seed_business_user(db_session, biz_id, user_id, role="owner")

    _patch_supabase_auth(
        monkeypatch,
        lambda _req: httpx.Response(
            status_code=200,
            json={"user": {"id": user_id, "email": "refresh@example.com"}},
        ),
    )

    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Login emite tanto access_token como refresh_token
            login_res = await client.post(
                "/api/v1/auth/login",
                json={"email": "refresh@example.com", "password": "secret"},
            )
            assert login_res.status_code == 200
            assert "access_token" in login_res.cookies
            assert "refresh_token" in login_res.cookies
            refresh_cookie = login_res.cookies["refresh_token"]
            access_cookie = login_res.cookies["access_token"]

            # 2. Refresh sin cookie -> 401
            client.cookies.clear()
            no_cookie_res = await client.post("/api/v1/auth/refresh")
            assert no_cookie_res.status_code == 401
            assert no_cookie_res.json()["code"] == "UNAUTHENTICATED"

            # 3. Usar access_token como refresh_token -> 401
            client.cookies.clear()
            access_as_refresh = await client.post(
                "/api/v1/auth/refresh",
                cookies={"refresh_token": access_cookie},
            )
            assert access_as_refresh.status_code == 401

            # 4. Usar refresh_token como access_token en /me -> 401
            client.cookies.clear()
            refresh_as_access = await client.get(
                "/api/v1/auth/me",
                cookies={"access_token": refresh_cookie},
            )
            assert refresh_as_access.status_code == 401

            # 5. Refresh válido -> 200 con nuevas cookies y LoginResponse
            client.cookies.clear()
            refresh_res = await client.post(
                "/api/v1/auth/refresh",
                cookies={"refresh_token": refresh_cookie},
            )
            assert refresh_res.status_code == 200
            assert "access_token" in refresh_res.cookies
            assert "refresh_token" in refresh_res.cookies
            body = refresh_res.json()
            assert body["requires_onboarding"] is False
            assert body["business"]["id"] == biz_id
    finally:
        await _cleanup_businesses(db_session, [biz_id])
