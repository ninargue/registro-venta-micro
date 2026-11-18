import time
import uuid

import httpx
import jwt
import pytest

from app.core.config import get_settings
from app.main import app

TEST_JWT_SECRET = "test-jwt-secret-key-for-auth-schemas-only-32bytes"


@pytest.fixture
def auth_test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUPABASE_URL", "https://supabase.test.local")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "test-anon-key")
    monkeypatch.setenv("JWT_SECRET_KEY", TEST_JWT_SECRET)
    monkeypatch.setenv("COOKIE_SECURE", "false")
    if hasattr(get_settings, "cache_clear"):
        get_settings.cache_clear()


def _make_session_cookie(user_id: str | None = None) -> dict[str, str]:
    now = int(time.time())
    payload = {
        "sub": user_id or str(uuid.uuid4()),
        "email": "owner@example.com",
        "business_id": None,
        "role": None,
        "iat": now,
        "exp": now + 900,
    }
    token = jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")
    return {"access_token": token}


@pytest.mark.parametrize(
    "invalid_timezone",
    [
        "Invalid/Timezone",
        "Mars/Olympus",
        "",
        "   ",
        "America/Argentina/Buenos_Aires_Exceeding_Fifty_Chars",
    ],
)
async def test_onboarding_rejects_invalid_or_unrecognized_iana_timezone(
    auth_test_env: None,
    invalid_timezone: str,
) -> None:
    """Scenario: Onboarding with invalid or unrecognized IANA timezone."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
        cookies=_make_session_cookie(),
    ) as client:
        response = await client.post(
            "/api/v1/auth/onboarding",
            json={
                "name": "Kiosco Central",
                "country": "AR",
                "timezone": invalid_timezone,
            },
        )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "Kiosco Central", "country": "XX"},
        {"name": "Kiosco Central", "country": "ARG"},
        {"name": "Kiosco Central", "country": "A"},
        {"name": "Kiosco Central", "country": ""},
        {"name": "", "country": "AR"},
        {"name": "   ", "country": "AR"},
        {"name": "A" * 101, "country": "AR"},
    ],
)
async def test_onboarding_rejects_unsupported_or_invalid_country_or_blank_name(
    auth_test_env: None,
    payload: dict[str, str],
) -> None:
    """Scenario: Onboarding with unsupported or invalid country code."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
        cookies=_make_session_cookie(),
    ) as client:
        response = await client.post("/api/v1/auth/onboarding", json=payload)

    assert response.status_code == 422


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "not-an-email", "password": "secret"},
        {"email": "", "password": "secret"},
        {"email": "owner@example.com", "password": ""},
    ],
)
async def test_login_rejects_malformed_payload(
    auth_test_env: None,
    payload: dict[str, str],
) -> None:
    """Validate login request schema rejects invalid email or empty password."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/auth/login", json=payload)

    assert response.status_code == 422
