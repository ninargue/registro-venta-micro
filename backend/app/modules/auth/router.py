from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.db import get_db
from app.core.rate_limit import login_rate_limiter
from app.core.security import CurrentUser, get_current_user
from app.modules.auth.repository import AuthRepository
from app.modules.auth.schemas import (
    BusinessResponse,
    ErrorResponse,
    LoginRequest,
    LoginResponse,
    OnboardingRequest,
)
from app.modules.auth.service import (
    AuthRateLimitError,
    AuthService,
    AuthUpstreamError,
    AuthUpstreamTimeoutError,
    BusinessAlreadyExistsError,
    InvalidCredentialsError,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def get_auth_service(
    request: Request,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AuthService:
    """Construye AuthService con su repositorio, configuración y cliente HTTP compartido."""
    http_client = getattr(request.app.state, "http_client", None)
    return AuthService(repository=AuthRepository(db), settings=settings, http_client=http_client)


def _set_session_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        key=settings.cookie_name,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        path="/",
        max_age=settings.access_token_expire_minutes * 60,
    )


def _error_json(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(code=code, message=message, details=None).model_dump(),
    )


@router.post(
    "/login",
    response_model=LoginResponse,
    responses={
        401: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    service: AuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
) -> LoginResponse | JSONResponse:
    """Autentica usuario contra Supabase Auth y emite cookie HttpOnly con JWT."""
    client_ip = request.client.host if request.client else "unknown"
    window = settings.login_rate_limit_window_seconds
    if not login_rate_limiter.check_and_record(
        f"ip:{client_ip}", settings.login_rate_limit_ip_max, window
    ) or not login_rate_limiter.check_and_record(
        f"email:{payload.email}", settings.login_rate_limit_email_max, window
    ):
        return _error_json(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "RATE_LIMIT_EXCEEDED",
            "Too many login attempts",
        )

    try:
        login_response, token = await service.login(payload)
    except InvalidCredentialsError:
        return _error_json(
            status.HTTP_401_UNAUTHORIZED,
            "INVALID_CREDENTIALS",
            "Invalid email or password",
        )
    except AuthRateLimitError:
        return _error_json(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "UPSTREAM_RATE_LIMITED",
            "Authentication service rate limit exceeded",
        )
    except AuthUpstreamTimeoutError:
        return _error_json(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "AUTH_UPSTREAM_TIMEOUT",
            "Authentication service timed out",
        )
    except AuthUpstreamError:
        return _error_json(
            status.HTTP_502_BAD_GATEWAY,
            "AUTH_UPSTREAM_UNAVAILABLE",
            "Authentication service unavailable",
        )

    _set_session_cookie(response, token, settings)
    return login_response


@router.post(
    "/onboarding",
    response_model=BusinessResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
async def onboarding(
    payload: OnboardingRequest,
    response: Response,
    current_user: CurrentUser = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
) -> BusinessResponse | JSONResponse:
    """Crea el comercio único del usuario autenticado y refresca la cookie JWT."""
    try:
        business_response, token = await service.onboard(current_user, payload)
    except BusinessAlreadyExistsError:
        return _error_json(
            status.HTTP_409_CONFLICT,
            "BUSINESS_ALREADY_EXISTS",
            "User already belongs to a business",
        )

    _set_session_cookie(response, token, settings)
    return business_response
