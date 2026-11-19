from typing import Any

from pydantic import BaseModel


def reject_nul_byte(value: str) -> str:
    """Rechaza cadenas que contengan bytes NUL (\\x00)."""
    if "\x00" in value:
        raise ValueError("Input must not contain NUL bytes")
    return value


class ErrorResponse(BaseModel):
    """Estructura estándar de error en respuestas HTTP de la API."""

    code: str
    message: str
    details: Any | None = None
