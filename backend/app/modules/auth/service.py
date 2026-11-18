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


class AuthRateLimitError(Exception):
    """Error lanzado cuando Supabase Auth responde 429 Too Many Requests."""


class AuthUpstreamTimeoutError(Exception):
    """Error lanzado cuando Supabase Auth excede el timeout de red."""


class AuthUpstreamError(Exception):
    """Error lanzado cuando Supabase Auth responde 5xx o falla el transporte."""


class BusinessAlreadyExistsError(Exception):
    """Error lanzado cuando el usuario ya tiene un comercio asignado."""


def _is_unique_violation(exc: IntegrityError) -> bool:
    orig = exc.orig
    if orig is None:
        return False
    cause = getattr(orig, "__cause__", None)
    sqlstate = (
        getattr(orig, "sqlstate", None)
        or getattr(orig, "pgcode", None)
        or getattr(cause, "sqlstate", None)
        or getattr(cause, "pgcode", None)
    )
    constraint_name = getattr(orig, "constraint_name", None) or getattr(
        cause, "constraint_name", None
    )
    return sqlstate == "23505" and (
        constraint_name == "uq_business_users_user_id"
        or "uq_business_users_user_id" in str(orig)
    )


class AuthService:
    """Casos de uso de autenticación y onboarding."""

    def __init__(
        self,
        repository: AuthRepository,
        settings: Settings,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._repository = repository
        self._settings = settings
        self._http_client = http_client

    async def _post_supabase_token(
        self,
        url: str,
        headers: dict[str, str],
        email: str,
        password: str,
    ) -> httpx.Response:
        if self._http_client is not None:
            return await self._http_client.post(
                url,
                params={"grant_type": "password"},
                headers=headers,
                json={"email": email, "password": password},
            )
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0)) as client:
            return await client.post(
                url,
                params={"grant_type": "password"},
                headers=headers,
                json={"email": email, "password": password},
            )

    async def _authenticate_supabase(self, email: str, password: str) -> tuple[uuid.UUID, str]:
        if not self._settings.supabase_url or not self._settings.supabase_anon_key:
            raise RuntimeError("Supabase Auth settings are not configured")

        url = f"{self._settings.supabase_url.rstrip('/')}/auth/v1/token"
        headers = {
            "apikey": self._settings.supabase_anon_key,
            "Content-Type": "application/json",
        }

        try:
            response = await self._post_supabase_token(url, headers, email, password)
        except httpx.TimeoutException as exc:
            raise AuthUpstreamTimeoutError("Supabase Auth request timed out") from exc
        except httpx.RequestError as exc:
            raise AuthUpstreamError("Supabase Auth transport failure") from exc

        if response.status_code == 429:
            raise AuthRateLimitError("Supabase Auth rate limit exceeded")
        if response.status_code >= 500:
            raise AuthUpstreamError(f"Supabase Auth upstream error: {response.status_code}")
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

        if payload.timezone is None:
            raise ValueError("Timezone must be resolved before onboarding")

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
            created_at=business.created_at,
        )
        return response, token
