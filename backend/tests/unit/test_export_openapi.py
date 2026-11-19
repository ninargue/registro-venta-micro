"""Pruebas unitarias para la exportación estática de OpenAPI y consistencia de schemas."""

import json
from pathlib import Path

from app.modules.auth.schemas import COUNTRY_TIMEZONES
from app.scripts.export_openapi import export_openapi


def test_export_openapi_generates_valid_schema(tmp_path: Path) -> None:
    output_path = export_openapi()
    assert output_path.exists(), "El archivo docs/openapi.json debe ser generado"

    content = output_path.read_text(encoding="utf-8")
    schema = json.loads(content)

    assert "openapi" in schema
    assert "info" in schema
    assert "paths" in schema
    assert "/api/v1/health" in schema["paths"]
    assert "/api/v1/auth/login" in schema["paths"]
    assert "/api/v1/auth/onboarding" in schema["paths"]


def test_country_timezones_catalog_is_valid() -> None:
    assert len(COUNTRY_TIMEZONES) > 0
    for code, tz in COUNTRY_TIMEZONES.items():
        assert len(code) == 2, f"El código de país {code} debe ser ISO alpha-2"
        assert "/" in tz or tz == "UTC", f"La zona horaria {tz} debe ser IANA"
