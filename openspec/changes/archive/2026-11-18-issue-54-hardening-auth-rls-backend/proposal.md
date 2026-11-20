# Proposal: Endurecimiento Backend Auth, RLS Context y Resiliencia (`issue-54-hardening-auth-rls-backend`)

## Why
La auditoría red-team sobre el PR #52 (issue #54) identificó brechas de seguridad, resiliencia y consistencia en el backend:
1. `AuthService._authenticate_supabase` instancia `httpx.AsyncClient` por request, enmascara `429`/`5xx` como `401` y no captura timeouts/errores de red (`500`), sin rate limiting por IP/email en FastAPI.
2. Inconsistencia en respuestas de error (`ErrorResponse` plano vs `{"detail": ...}` de `HTTPException`/`422`).
3. Falta de validación de secretos/config al arranque (`JWT_SECRET_KEY >= 32` bytes, algoritmo HMAC permitido, `COOKIE_SECURE` en producción) y permisividad en `decode_access_token` (`business_id` no-string o inconsistente con `role`).
4. Posible GUC residual (`app.current_business_id`) en `set_rls_user_context`, `InvalidRequestError` en transacciones anidadas, byte `\x00` no rechazado (`500` en `asyncpg`), `_is_unique_violation` demasiado amplio y uso de `assert` en código productivo.

## What
- Cliente `httpx.AsyncClient` compartido en `app.state.http_client` vía lifespan de FastAPI, mapeo explícito de `429`/`5xx`/timeouts a `429`/`502`/`503`, y rate limiter en memoria por IP/email para `POST /api/v1/auth/login`.
- Exception handlers unificados (`HTTPException`, `RequestValidationError`) en `backend/app/main.py` usando `ErrorResponse`.
- Validación de configuración (`JWT_SECRET_KEY >= 32` bytes, `jwt_algorithm` HMAC, `COOKIE_SECURE=false` bloqueado en `production`) y validación estricta de claims en `decode_access_token`.
- Limpieza de `app.current_business_id`/`app.current_user_role` en `set_rls_user_context`, soporte seguro de transacciones anidadas en `AuthRepository`, y reemplazo de `assert` en `db.py` y `service.py`.
- Rechazo de byte NUL (`\x00`) y `max_length` en `LoginRequest`; `_is_unique_violation` estricto (`23505` + `uq_business_users_user_id`).
- Documentación de variables de entorno y rol runtime `app_runtime` en `backend/.env.example`.

## Non-goals
- Implementación de `/refresh`, `/logout` y `/me` (hallazgo 9, diferido a otro issue según indicación del usuario).
- Cambios en migraciones o políticas RLS de base de datos (cubiertos en `issue-54-hardening-auth-rls-db`).

## Compatibility
- Mantiene los contratos de éxito `200`/`201` de `/api/v1/auth/login` y `/api/v1/auth/onboarding`.
- Unifica el formato de error en `ErrorResponse` (`code`, `message`, `details`).
