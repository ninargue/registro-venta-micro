# Design: Endurecimiento Backend Auth, RLS Context y Resiliencia (`issue-54-hardening-auth-rls-backend`)

## Convenciones de infraestructura detectadas
- `backend_dir`: `backend/app`
- `tests_dir`: `backend/tests`
- `test_cmd`: `cd backend && uv run pytest`
- `lint_cmd`: `cd backend && uv run ruff check .`
- `typecheck_cmd`: `cd backend && uv run mypy app`
- `db_mode`: `with-db` (PostgreSQL 17 vía Supabase local, migración `f8b2c1a94d07`)

## Decisiones de diseño
1. **Lifespan y cliente HTTP compartido (`app/main.py`):**
   - `lifespan(app)` valida la configuración crítica de arranque (`validate_runtime_settings(settings)`) cuando está configurada y crea `app.state.http_client = httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0))`, cerrándolo al finalizar.
   - `get_auth_service` inyecta `getattr(request.app.state, "http_client", None)`.
2. **Rate Limiter (`app/core/rate_limit.py`):**
   - Clase `SlidingWindowRateLimiter` con locks `asyncio.Lock` o estructura thread/async-safe en memoria, límite configurable por IP (`login_rate_limit_ip_max = 20`) y por email (`login_rate_limit_email_max = 10`) en `login_rate_limit_window_seconds = 60`.
3. **Exception Handlers (`app/main.py`):**
   - `StarletteHTTPException` -> `ErrorResponse`.
   - `RequestValidationError` -> `ErrorResponse(code="VALIDATION_ERROR", message="Validation error", details=...)` con errores serializables.
4. **Config y Seguridad (`app/core/config.py`, `app/core/security.py`):**
   - `Settings`: `app_env`, `jwt_algorithm: Literal["HS256", "HS384", "HS512"]`, validador de longitud `>= 32` bytes cuando `jwt_secret_key` no es `None`, y guardrail `cookie_secure=True` obligatorio si `app_env == "production"`.
   - `decode_access_token`: rechaza `raw_business_id` que no sea `None | str`, y exige `(business_id is None) == (role is None)`.
5. **DB Context y Repositorio (`app/core/db.py`, `app/modules/auth/repository.py`):**
   - `set_rls_user_context`: ejecuta `SET LOCAL ROLE app_api`, `set_config('app.current_user_id', ...)`, `set_config('app.current_business_id', '', true)` y `set_config('app.current_user_role', '', true)`.
   - `get_tenant_db`: reemplaza `assert` por `if current_user.business_id is None: raise HTTPException(403, ...)`.
   - `AuthRepository`: helper `_transaction()` que usa `begin_nested()` si `self._session.in_transaction()` o `begin()` en caso contrario.
6. **Schemas y Service (`app/modules/auth/schemas.py`, `app/modules/auth/service.py`):**
   - Validador `@field_validator` / helper `_reject_nul_byte` en `LoginRequest` y `OnboardingRequest`.
   - `LoginRequest`: `email: str = Field(max_length=254)`, `password: str = Field(min_length=1, max_length=128)`.
   - `_is_unique_violation`: verifica `sqlstate == "23505"` (en `orig` o `orig.__cause__`) **AND** `uq_business_users_user_id`.
   - Reemplaza `assert payload.timezone is not None` por validación explícita.
