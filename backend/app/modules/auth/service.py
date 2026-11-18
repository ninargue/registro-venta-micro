import uuid
from typing import cast

import httpx
from sqlalchemy.exc import IntegrityError

from app.core.config import Settings
from app.core.security import CurrentUser, RoleType, create_access_token
from app.modules.auth.repository import AuthRepository
from app.modules.auth.schemas import (
    BusinessResponse,
    BusinessSummary,
    LoginRequest,
    LoginResponse,
    OnboardingRequest,
    UserPayload,
)


class InvalidCredentialsError(Exception):
    """Error lanzado cuando Supabase Auth rechaza las credenciales."""


class BusinessAlreadyExistsError(Exception):
    """Error lanzado cuando el usuario ya tiene un comercio asignado."""


def _is_unique_violation(exc: IntegrityError) -> bool:
    orig = exc.orig
    if orig is None:
        return False
    sqlstate = getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)
    return sqlstate == "23505" or "uq_business_users_user_id" in str(orig)


class AuthService:
    """Casos de uso de autenticación y onboarding."""

    def __init__(self, repository: AuthRepository, settings: Settings) -> None:
        self._repository = repository
        self._settings = settings

    async def _authenticate_supabase(self, email: str, password: str) -> tuple[uuid.UUID, str]:
        if not self._settings.supabase_url or not self._settings.supabase_anon_key:
            raise RuntimeError("Supabase Auth settings are not configured")

        url = f"{self._settings.supabase_url.rstrip('/')}/auth/v1/token"
        headers = {
            "apikey": self._settings.supabase_anon_key,
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                url,
                params={"grant_type": "password"},
                headers=headers,
                json={"email": email, "password": password},
            )

        if response.status_code != 200:
            raise InvalidCredentialsError("Invalid email or password")

        data = response.json()
        user_data = data.get("user")
        if not isinstance(user_data, dict) or not isinstance(user_data.get("id"), str):
            raise InvalidCredentialsError("Invalid authentication response")

        try:
            user_id = uuid.UUID(user_data["id"])
        except ValueError as exc:
            raise InvalidCredentialsError("Invalid user identifier") from exc

        resolved_email = user_data.get("email")
        return user_id, str(resolved_email) if isinstance(resolved_email, str) else email

    async def login(self, payload: LoginRequest) -> tuple[LoginResponse, str]:
        """Autentica contra Supabase Auth, resuelve membresía y emite JWT."""
        user_id, email = await self._authenticate_supabase(payload.email, payload.password)
        membership = await self._repository.get_user_membership(user_id)

        if membership is None:
            token = create_access_token(
                user_id=user_id,
                email=email,
                business_id=None,
                role=None,
                settings=self._settings,
            )
            response = LoginResponse(
                user=UserPayload(id=user_id, email=email),
                requires_onboarding=True,
                business=None,
            )
            return response, token

        role = cast(RoleType, membership.role)
        token = create_access_token(
            user_id=user_id,
            email=email,
            business_id=membership.business.id,
            role=role,
            settings=self._settings,
        )
        response = LoginResponse(
            user=UserPayload(id=user_id, email=email),
            requires_onboarding=False,
            business=BusinessSummary(
                id=membership.business.id,
                name=membership.business.name,
                country=membership.business.country,
                timezone=membership.business.timezone,
                role=role,
            ),
        )
        return response, token

    async def onboard(
        self,
        current_user: CurrentUser,
        payload: OnboardingRequest,
    ) -> tuple[BusinessResponse, str]:
        """Crea comercio único para usuario autenticado y refresca JWT."""
        if current_user.business_id is not None:
            raise BusinessAlreadyExistsError("User already belongs to a business")

        assert payload.timezone is not None

        try:
            business = await self._repository.create_business_with_owner(
                user_id=current_user.user_id,
                name=payload.name,
                country=payload.country,
                timezone=payload.timezone,
            )
        except IntegrityError as exc:
            if _is_unique_violation(exc):
                raise BusinessAlreadyExistsError("User already belongs to a business") from exc
            raise

        token = create_access_token(
            user_id=current_user.user_id,
            email=current_user.email,
            business_id=business.id,
            role="owner",
            settings=self._settings,
        )
        response = BusinessResponse(
            id=business.id,
            name=business.name,
            country=business.country,
            timezone=business.timezone,
            role="owner",
            created_at=business.created_at,
        )
        return response, token
