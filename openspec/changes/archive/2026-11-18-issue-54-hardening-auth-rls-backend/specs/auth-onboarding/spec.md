# Delta Spec: auth-onboarding (Hardening Issue #54)

## ADDED Requirements

### Requirement: Resiliencia y mapeo de errores de Supabase Auth
`AuthService` SHALL reutilizar un `httpx.AsyncClient` compartido y mapear errores transitorios de Supabase Auth sin enmascararlos como `401`.

#### Scenario: Mapeo de rate limit 429 desde Supabase Auth
- **WHEN** Supabase Auth responde `429 Too Many Requests` en `POST /api/v1/auth/login`
- **THEN** el backend responde `429` con `ErrorResponse` (`code = "UPSTREAM_RATE_LIMITED"`) sin emitir cookie.

#### Scenario: Mapeo de errores 5xx y timeouts desde Supabase Auth
- **WHEN** Supabase Auth responde `502`/`503`/`500` o lanza `httpx.TimeoutException` / `httpx.RequestError`
- **THEN** el backend responde `502` o `503` con `ErrorResponse` (`code = "AUTH_UPSTREAM_UNAVAILABLE"` o `"AUTH_UPSTREAM_TIMEOUT"`) sin lanzar `500`.

### Requirement: Rate limiting por IP y email en login
`POST /api/v1/auth/login` SHALL aplicar rate limiting por IP cliente y por email normalizado antes de consultar a Supabase Auth.

#### Scenario: Bloqueo por exceso de intentos en login
- **WHEN** una IP o email supera el umbral configurado en la ventana de tiempo
- **THEN** el backend responde `429` con `ErrorResponse` (`code = "RATE_LIMIT_EXCEEDED"`) sin llamar a Supabase Auth.

### Requirement: Formato unificado ErrorResponse en toda la API
Todo error (`HTTPException`, `RequestValidationError` 422, errores de dominio) SHALL devolverse con el esquema plano `{code, message, details}`.

#### Scenario: Respuesta 401/403/422 con ErrorResponse uniforme
- **WHEN** ocurre un `401` de `get_current_user`, `403` de `get_current_tenant` o `422` de validación Pydantic
- **THEN** el JSON de respuesta contiene exactamente las claves `code`, `message` y `details` (sin envoltorio `detail`).

### Requirement: Validación estricta de configuración, JWT y entradas
La configuración SHALL validar `JWT_SECRET_KEY >= 32` bytes, algoritmo HMAC (`HS256`/`HS384`/`HS512`) y prohibir `COOKIE_SECURE=false` cuando `APP_ENV=production`. `decode_access_token` SHALL rechazar `business_id` no-string e inconsistencias entre `business_id` y `role`. Los esquemas de entrada SHALL rechazar bytes NUL (`\x00`) y aplicar `max_length` en `LoginRequest`.

#### Scenario: Rechazo de byte NUL en payloads de auth
- **WHEN** `LoginRequest` u `OnboardingRequest` contiene `\x00` en cualquier campo string
- **THEN** Pydantic rechaza la petición con `422` (`ErrorResponse`).

#### Scenario: Rechazo de JWT con claims inconsistentes o business_id no-string
- **WHEN** un JWT contiene `business_id` entero/booleano o `business_id` presente sin `role` (o viceversa)
- **THEN** `decode_access_token` rechaza el token con `401`.

### Requirement: Limpieza de GUC residual y transacciones seguras
`set_rls_user_context` SHALL limpiar `app.current_business_id` y `app.current_user_role` al iniciar un contexto de solo-usuario, y `AuthRepository` SHALL soportar sesiones con transacción ya iniciada sin lanzar `InvalidRequestError`.

#### Scenario: Aislamiento sin GUC residual en get_user_db
- **WHEN** una sesión ejecuta `set_rls_user_context` tras haber tenido `app.current_business_id` en una operación previa
- **THEN** `app.current_business_id` queda vacío en la transacción actual.
