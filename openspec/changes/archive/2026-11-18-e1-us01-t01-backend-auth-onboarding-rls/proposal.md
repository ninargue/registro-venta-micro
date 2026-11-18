<!--
Ticket: US-01-T01 | Issue: #39 (https://github.com/ninargue/registro-venta-micro/issues/39) | Capa: backend
-->

## Why

Los micronegocios necesitan autenticarse contra Supabase Auth y registrar su comercio en un flujo único de primer acceso para obtener el contexto de tenant (`business_id`) requerido por las políticas de Row-Level Security (RLS) en PostgreSQL. Habiéndose cerrado y archivado el contrato de base de datos e inmutabilidad en `#53` (`businesses-schema-and-rls`), la capa backend debe alinearse exactamente con ese contrato para desbloquear la PWA (`#40`) y los módulos de dominio (`#42`).

## What Changes

- **Endpoint de Login (`POST /api/v1/auth/login`)**: Valida credenciales contra Supabase Auth (`httpx`), abre transacción bajo el rol runtime `app_api` fijando `SET LOCAL app.current_user_id = '<user_id>'` para resolver la membresía en `business_users` sin deadlock RLS (y fija `SET LOCAL app.current_business_id` al leer `businesses`), y emite cookie `HttpOnly` con JWT propio (`requires_onboarding: true` cuando no hay negocio asociado).
- **Endpoint de Onboarding (`POST /api/v1/auth/onboarding`)**: Para usuarios autenticados sin comercio, genera `business_id = uuid4()` en Python, ejecuta `SET LOCAL app.current_user_id = '<user_id>'` y `SET LOCAL app.current_business_id = '<business_id>'` antes de `INSERT INTO businesses ... RETURNING` + `INSERT INTO business_users` (rol `owner`), valida país (`COUNTRY_TIMEZONES`) y zona horaria IANA con `zoneinfo.ZoneInfo`, maneja `UNIQUE (user_id)` ante reintentos/concurrencia con `409 Conflict` sin duplicados ni huérfanos, y refresca la cookie de sesión con el nuevo `business_id`.
- **Dependencias Transaccionales RLS y Seguridad (`core/db.py`, `core/security.py`)**: Validan el JWT de cookie y aplican `SET LOCAL ROLE app_api`, `app.current_user_id` y `app.current_business_id` por transacción.
- **Contrato de BD Inmutable (`capa:db` cerrada)**: Se eliminan tareas de creación de modelos ORM o migraciones Alembic; el backend consume `backend/app/modules/auth/models.py` y las migraciones `0002`/`0003` sin modificarlos.
- **Non-goals**: Modificar `backend/migrations/` o `models.py` (inmutables tras `#53`); login social (OAuth); recuperación de contraseña o UI de frontend (`#40`); soporte multi-negocio o invitación de cajeros (fuera del MVP).

## Capabilities

### New Capabilities
- `auth-onboarding`: Autenticación de usuarios contra Supabase Auth, aprovisionamiento de comercio único con validación IANA de `timezone` (`ZoneInfo`), manejo idempotente de conflictos `UNIQUE (user_id)` y propagación transaccional del contexto RLS (`app.current_user_id` + `app.current_business_id`).

### Modified Capabilities
*(Ninguna)*

## Impact

- **Backend (`backend/app`)**: Nuevo código en `backend/app/modules/auth/` (`schemas.py`, `repository.py`, `service.py`, `router.py`), `backend/app/core/` (`config.py`, `db.py`, `security.py`), `backend/app/main.py` y dependencia `tzdata` en `backend/pyproject.toml` (vía `uv add`).
- **Base de Datos (Inmutable)**: Consume `backend/app/modules/auth/models.py` y migraciones `0002`/`0003` sin cambios (`Gate 3` No-DB-Diff).
- **Consumidores**: Desbloquea el frontend de login/onboarding ([Issue #40](https://github.com/ninargue/registro-venta-micro/issues/40)) y el módulo de catálogo ([Issue #42](https://github.com/ninargue/registro-venta-micro/issues/42)).
