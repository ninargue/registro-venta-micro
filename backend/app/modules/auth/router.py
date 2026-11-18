from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.db import get_db
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
    AuthService,
    BusinessAlreadyExistsError,
    InvalidCredentialsError,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def get_auth_service(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AuthService:
    """Construye AuthService con su repositorio y configuración."""
    return AuthService(repository=AuthRepository(db), settings=settings)


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


@router.post(
    "/login",
    response_model=LoginResponse,
    responses={
        401: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
async def login(
    payload: LoginRequest,
    response: Response,
    service: AuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
) -> LoginResponse | JSONResponse:
    """Autentica usuario contra Supabase Auth y emite cookie HttpOnly con JWT."""
    try:
        login_response, token = await service.login(payload)
    except InvalidCredentialsError:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=ErrorResponse(
                code="INVALID_CREDENTIALS",
                message="Invalid email or password",
                details=None,
            ).model_dump(),
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
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=ErrorResponse(
                code="BUSINESS_ALREADY_EXISTS",
                message="User already belongs to a business",
                details=None,
            ).model_dump(),
        )

    _set_session_cookie(response, token, settings)
    return business_response
