import time
import uuid
from dataclasses import dataclass
from typing import Any, Literal, cast

import jwt
from fastapi import Depends, HTTPException, Request, status

from app.core.config import Settings, get_settings

RoleType = Literal["owner", "cashier"]


@dataclass(frozen=True, slots=True)
class CurrentUser:
    """Identidad y contexto de tenant extraídos del JWT de sesión."""

    user_id: uuid.UUID
    email: str
    business_id: uuid.UUID | None = None
    role: RoleType | None = None


def _require_jwt_secret(settings: Settings) -> str:
    if not settings.jwt_secret_key:
        raise RuntimeError("JWT_SECRET_KEY is not configured")
    return settings.jwt_secret_key


def create_access_token(
    *,
    user_id: uuid.UUID,
    email: str,
    business_id: uuid.UUID | None = None,
    role: RoleType | None = None,
    settings: Settings,
) -> str:
    """Firma un JWT de sesión con expiración configurada."""
    secret = _require_jwt_secret(settings)
    now = int(time.time())
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "email": email,
        "business_id": str(business_id) if business_id is not None else None,
        "role": role,
        "iat": now,
        "exp": now + settings.access_token_expire_minutes * 60,
    }
    return jwt.encode(payload, secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str, settings: Settings) -> CurrentUser:
    """Valida y decodifica el JWT de sesión; lanza 401 si es inválido o expiró."""
    secret = _require_jwt_secret(settings)
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "exp", "iat"]},
        )
        sub = payload.get("sub")
        email = payload.get("email")
        raw_business_id = payload.get("business_id")
        raw_role = payload.get("role")
        if not isinstance(sub, str) or not isinstance(email, str):
            raise ValueError("Invalid token claims")
        user_id = uuid.UUID(sub)
        if raw_business_id is not None and not isinstance(raw_business_id, str):
            raise ValueError("Invalid business_id claim")
        business_id = uuid.UUID(raw_business_id) if raw_business_id is not None else None
        if raw_role is not None and raw_role not in ("owner", "cashier"):
            raise ValueError("Invalid role claim")
        role = cast(RoleType | None, raw_role)
        if (business_id is None) != (role is None):
            raise ValueError("Inconsistent business_id and role claims")
    except (jwt.PyJWTError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "UNAUTHENTICATED",
                "message": "Invalid or expired session",
                "details": None,
            },
        ) from exc

    return CurrentUser(
        user_id=user_id,
        email=email,
        business_id=business_id,
        role=role,
    )


def get_current_user(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> CurrentUser:
    """Extrae y valida el usuario autenticado desde la cookie HttpOnly."""
    token = request.cookies.get(settings.cookie_name)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "UNAUTHENTICATED",
                "message": "Authentication required",
                "details": None,
            },
        )
    return decode_access_token(token, settings)


def get_current_tenant(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """Exige que el usuario autenticado tenga un comercio activo en el JWT."""
    if current_user.business_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "ONBOARDING_REQUIRED",
                "message": "Business onboarding required",
                "details": None,
            },
        )
    return current_user
