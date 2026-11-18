import asyncio
import importlib.util
import time
import uuid
from collections.abc import Callable
from typing import Any

import httpx
import jwt
import pytest
from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.main import app

TEST_SUPABASE_URL = "https://supabase.test.local"
TEST_SUPABASE_ANON_KEY = "test-supabase-anon-key"
TEST_JWT_SECRET = "test-jwt-secret-key-for-integration-tests-32b"


@pytest.fixture
def auth_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SUPABASE_URL", TEST_SUPABASE_URL)
    monkeypatch.setenv("SUPABASE_ANON_KEY", TEST_SUPABASE_ANON_KEY)
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
        async with httpx.AsyncClient(transport=transport, base_url="https://test") as client:
            response = await client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": "valid-password"},
            )

        assert response.status_code == 200
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

        async with db_session.begin():
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
    """Scenarios: Valid tenant context set on transactional session + Cross-tenant isolation."""
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
