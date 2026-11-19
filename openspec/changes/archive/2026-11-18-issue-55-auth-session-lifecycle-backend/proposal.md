# Proposal: Endpoints de ciclo de sesión (`/auth/me`, `/auth/logout`, `/auth/refresh`) (`issue-55-auth-session-lifecycle-backend`)

## Why
Al operar con cookies `HttpOnly` (no accesibles desde JavaScript), la PWA necesita endpoints explícitos para:
1. Rehidratar el estado de sesión y comercio activo tras recargar la pestaña (`GET /api/v1/auth/me`).
2. Renovar el `access_token` de 15 minutos sin interrumpir la operación en mostrador (`POST /api/v1/auth/refresh`).
3. Cerrar sesión limpiando de forma segura las cookies `HttpOnly` (`POST /api/v1/auth/logout`).

## What Changes
- `core/config.py` y `core/security.py`: configuración de `refresh_cookie_name` y `refresh_token_expire_days`, emisión y validación estricta de `refresh_token` (`token_type = "refresh"`), y rechazo de `refresh_token` usado como `access_token`.
- `modules/auth/router.py` y `service.py`:
  - Emisión de cookie `refresh_token` `HttpOnly; Secure; SameSite=Strict` en `/login` y `/onboarding`.
  - `GET /api/v1/auth/me`: consulta identidad y membresía actual bajo RLS y devuelve `LoginResponse` (`401` `ErrorResponse` si no hay sesión válida).
  - `POST /api/v1/auth/logout`: elimina `access_token` y `refresh_token` con `Max-Age=0` y mismos atributos de seguridad (`204 No Content`).
  - `POST /api/v1/auth/refresh`: valida `refresh_token`, consulta membresía actual en BD bajo RLS, re-emite `access_token` y `refresh_token`, y devuelve `200` con `LoginResponse` (`401` si falta o es inválido/expirado).
- Tests unitarios y de integración en `backend/tests/integration/test_auth_onboarding.py`.

## Non-goals
- Tabla de revocación / detección de reuso de refresh tokens en BD (descartada en `docs/prd/0001_alcance_mvp.md`).
- Cambios de esquema o migraciones de base de datos.

## Compatibility
- 100% compatible con `/login` y `/onboarding` existentes; agrega la cookie `refresh_token` a sus respuestas `200`/`201`.
