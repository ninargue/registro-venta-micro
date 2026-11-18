import re
import uuid
from datetime import datetime
from typing import Any, Literal, Self
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, field_validator, model_validator

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

COUNTRY_TIMEZONES: dict[str, str] = {
    "AR": "America/Argentina/Buenos_Aires",
    "UY": "America/Montevideo",
    "CL": "America/Santiago",
    "CO": "America/Bogota",
    "MX": "America/Mexico_City",
    "PE": "America/Lima",
    "PY": "America/Asuncion",
    "BO": "America/La_Paz",
    "EC": "America/Guayaquil",
    "BR": "America/Sao_Paulo",
    "ES": "Europe/Madrid",
    "US": "America/New_York",
}


def _validate_iana_timezone(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("Timezone cannot be empty")
    if len(cleaned) > 50:
        raise ValueError("Timezone must be at most 50 characters")
    try:
        ZoneInfo(cleaned)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"Invalid IANA timezone: {cleaned}") from exc
    return cleaned


class LoginRequest(BaseModel):
    """Credenciales de entrada para POST /api/v1/auth/login."""

    email: str
    password: str = Field(min_length=1)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if not EMAIL_REGEX.match(cleaned):
            raise ValueError("Invalid email format")
        return cleaned


class UserPayload(BaseModel):
    """Datos básicos del usuario autenticado."""

    id: uuid.UUID
    email: str


class BusinessSummary(BaseModel):
    """Resumen del comercio asociado al usuario."""

    id: uuid.UUID
    name: str
    country: str
    timezone: str
    role: Literal["owner", "cashier"]


class LoginResponse(BaseModel):
    """Respuesta de login con estado de onboarding y comercio opcional."""

    user: UserPayload
    requires_onboarding: bool
    business: BusinessSummary | None = None


class OnboardingRequest(BaseModel):
    """Payload de creación de comercio en POST /api/v1/auth/onboarding."""

    name: str
    country: str
    timezone: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Business name cannot be empty")
        if len(cleaned) > 100:
            raise ValueError("Business name must be at most 100 characters")
        return cleaned

    @field_validator("country")
    @classmethod
    def validate_country(cls, value: str) -> str:
        cleaned = value.strip().upper()
        if len(cleaned) != 2 or cleaned not in COUNTRY_TIMEZONES:
            raise ValueError(f"Unsupported country code: {value}")
        return cleaned

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _validate_iana_timezone(value)

    @model_validator(mode="after")
    def resolve_default_timezone(self) -> Self:
        if self.timezone is None:
            resolved = COUNTRY_TIMEZONES[self.country]
            self.timezone = _validate_iana_timezone(resolved)
        return self


class BusinessResponse(BaseModel):
    """Respuesta de comercio creado en POST /api/v1/auth/onboarding."""

    id: uuid.UUID
    name: str
    country: str
    timezone: str
    role: Literal["owner", "cashier"] = "owner"
    created_at: datetime


class ErrorResponse(BaseModel):
    """Estructura estándar de error en endpoints de autenticación."""

    code: str
    message: str
    details: Any | None = None
