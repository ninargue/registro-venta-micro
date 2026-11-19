"""Pruebas unitarias para la exportación estática de OpenAPI y consistencia de schemas."""

import json
from pathlib import Path

from app.modules.auth.schemas import COUNTRY_TIMEZONES
from app.scripts.export_openapi import check_openapi, export_openapi


def test_export_openapi_generates_valid_schema(tmp_path: Path) -> None:
    target = tmp_path / "openapi.json"
    output_path = export_openapi(target)
    assert output_path == target
    assert output_path.exists(), "El archivo openapi.json debe ser generado"

    content = output_path.read_text(encoding="utf-8")
    schema = json.loads(content)

    assert "openapi" in schema
    assert "info" in schema
    assert "paths" in schema
    assert "/api/v1/health" in schema["paths"]
    assert "/api/v1/auth/login" in schema["paths"]
    assert "/api/v1/auth/onboarding" in schema["paths"]


def test_check_openapi_returns_zero_when_up_to_date(tmp_path: Path) -> None:
    target = tmp_path / "openapi.json"
    export_openapi(target)
    assert check_openapi(target) == 0


def test_check_openapi_returns_nonzero_and_does_not_overwrite_on_drift(tmp_path: Path) -> None:
    target = tmp_path / "openapi.json"
    export_openapi(target)
    stale_content = target.read_text(encoding="utf-8").replace(
        "/api/v1/health",
        "/api/v1/salud",
    )
    target.write_bytes(stale_content.encode("utf-8"))

    exit_code = check_openapi(target)

    assert exit_code == 1
    assert target.read_text(encoding="utf-8") == stale_content


def test_check_openapi_returns_nonzero_when_missing(tmp_path: Path) -> None:
    missing_target = tmp_path / "missing-openapi.json"
    assert check_openapi(missing_target) == 1


def test_country_timezones_catalog_is_valid() -> None:
    assert len(COUNTRY_TIMEZONES) > 0
    for code, tz in COUNTRY_TIMEZONES.items():
        assert len(code) == 2, f"El código de país {code} debe ser ISO alpha-2"
        assert "/" in tz or tz == "UTC", f"La zona horaria {tz} debe ser IANA"
