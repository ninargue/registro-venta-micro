from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import get_settings, validate_runtime_settings
from app.core.schemas import ErrorResponse
from app.modules.auth.router import router as auth_router
from app.modules.catalog.router import router as catalog_router
from app.modules.health.router import router as health_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Valida configuración crítica y gestiona el cliente HTTP compartido."""
    settings = get_settings()
    validate_runtime_settings(settings)
    http_client = httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0))
    app.state.http_client = http_client
    try:
        yield
    finally:
        await http_client.aclose()


app = FastAPI(title="registro-venta-micro API", lifespan=lifespan)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Unifica todas las HTTPException al esquema plano ErrorResponse."""
    if isinstance(exc.detail, dict) and "code" in exc.detail and "message" in exc.detail:
        payload = ErrorResponse(
            code=str(exc.detail["code"]),
            message=str(exc.detail["message"]),
            details=exc.detail.get("details"),
        )
    else:
        payload = ErrorResponse(
            code="HTTP_ERROR",
            message=str(exc.detail),
            details=None,
        )
    return JSONResponse(status_code=exc.status_code, content=payload.model_dump())


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    _request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Unifica errores de validación Pydantic (422) al esquema plano ErrorResponse."""
    payload = ErrorResponse(
        code="VALIDATION_ERROR",
        message="Validation error",
        details=jsonable_encoder(exc.errors()),
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=payload.model_dump(),
    )


app.include_router(health_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(catalog_router, prefix="/api/v1")
