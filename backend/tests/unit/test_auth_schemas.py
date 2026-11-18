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


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "user\x00@example.com", "password": "secret"},
        {"email": "user@example.com", "password": "sec\x00ret"},
        {"email": ("a" * 245) + "@example.com", "password": "secret"},
        {"email": "user@example.com", "password": "p" * 129},
    ],
)
async def test_login_rejects_nul_byte_and_excessive_length(
    auth_test_env: None,
    payload: dict[str, str],
) -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/auth/login", json=payload)

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert "detail" not in body


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "Kiosco\x00Central", "country": "AR"},
        {
            "name": "Kiosco Central",
            "country": "AR",
            "timezone": "America/Argentina\x00/Buenos_Aires",
        },
    ],
)
async def test_onboarding_rejects_nul_byte(
    auth_test_env: None,
    payload: dict[str, str],
) -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
        cookies=_make_session_cookie(),
    ) as client:
        response = await client.post("/api/v1/auth/onboarding", json=payload)

    assert response.status_code == 422


def test_settings_rejects_short_jwt_secret_and_insecure_cookie_in_production() -> None:
    from pydantic import ValidationError

    from app.core.config import Settings

    with pytest.raises(ValidationError):
        Settings(database_url="postgresql+asyncpg://u:p@localhost:5432/db", jwt_secret_key="short")

    with pytest.raises(ValidationError):
        Settings(
            database_url="postgresql+asyncpg://u:p@localhost:5432/db",
            jwt_secret_key="a" * 32,
            jwt_algorithm="none",  # type: ignore[arg-type]
        )

    with pytest.raises(ValidationError):
        Settings(
            database_url="postgresql+asyncpg://u:p@localhost:5432/db",
            jwt_secret_key="a" * 32,
            app_env="production",
            cookie_secure=False,
        )


def test_decode_access_token_rejects_non_string_business_id_and_role_mismatch() -> None:
    from fastapi import HTTPException

    from app.core.config import Settings
    from app.core.security import decode_access_token

    settings = Settings(
        database_url="postgresql+asyncpg://u:p@localhost:5432/db",
        jwt_secret_key=TEST_JWT_SECRET,
        cookie_secure=False,
    )
    now = int(time.time())

    # business_id no-string (int)
    bad_type_token = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "email": "owner@example.com",
            "business_id": 12345,
            "role": None,
            "iat": now,
            "exp": now + 900,
        },
        TEST_JWT_SECRET,
        algorithm="HS256",
    )
    with pytest.raises(HTTPException) as exc_type:
        decode_access_token(bad_type_token, settings)
    assert exc_type.value.status_code == 401

    # business_id presente sin role
    missing_role_token = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "email": "owner@example.com",
            "business_id": str(uuid.uuid4()),
            "role": None,
            "iat": now,
            "exp": now + 900,
        },
        TEST_JWT_SECRET,
        algorithm="HS256",
    )
    with pytest.raises(HTTPException) as exc_missing_role:
        decode_access_token(missing_role_token, settings)
    assert exc_missing_role.value.status_code == 401

    # role presente sin business_id
    missing_biz_token = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "email": "owner@example.com",
            "business_id": None,
            "role": "owner",
            "iat": now,
            "exp": now + 900,
        },
        TEST_JWT_SECRET,
        algorithm="HS256",
    )
    with pytest.raises(HTTPException) as exc_missing_biz:
        decode_access_token(missing_biz_token, settings)
    assert exc_missing_biz.value.status_code == 401
