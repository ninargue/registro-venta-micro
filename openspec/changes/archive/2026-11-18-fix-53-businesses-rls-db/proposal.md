<!--
Ticket: N/A | Issue: #53 (https://github.com/ninargue/registro-venta-micro/issues/53) | Capa: db
Contexto: Bloquea #39 (PR #52) — Hallazgos de revisión adversarial sobre businesses-schema-and-rls
-->

## Why

La auditoría adversarial sobre `businesses-schema-and-rls` (PR #52 / Issue #39) detectó vulnerabilidades críticas de RLS y un deadlock de login que bloquean `#39`. Al autenticar credenciales, el backend conoce solo el `user_id`, pero `business_users` exige `app.current_business_id`, impidiendo resolver la membresía. Además, `business_users_onboarding_insert` usa `WITH CHECK (true)`, falta unicidad sobre `user_id` para el modelo de comercio único del MVP, y el rol `app_api` carece de permisos DCL explícitos.

## What Changes

- **Resolución de deadlock de login (`SELECT` RLS en `business_users`)**: Sustituir la política `FOR ALL` por políticas granulares y permitir lectura cuando `user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid`, manteniendo el aislamiento por `app.current_business_id` (**Decisión explícita Opción A**: se conserva `app.current_business_id` sin renombrar a `app.tenant_id` y se incorpora `app.current_user_id`).
- **Restricción de inserción (`INSERT` RLS en `business_users`)**: Reemplazar `WITH CHECK (true)` exigiendo `user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid` (y consistencia con `app.current_business_id` si está presente).
- **Unicidad de comercio por usuario (`UNIQUE (user_id)`)**: Incorporar `uq_business_users_user_id` en `business_users` (reemplazando el índice no único `ix_business_users_user_id` y actualizando `BusinessUser` en `models.py` para `alembic check`), garantizando comercio único e idempotencia en onboarding.
- **Permisos DCL para `app_api`**: Asegurar existencia no privilegiada de `app_api` (`NOSUPERUSER NOBYPASSRLS`) en entornos efímeros/locales y otorgar permisos DML sobre `businesses` y `business_users` bajo RLS forzada.
- **Tests adversariales**: Ampliar `backend/tests/integration/test_db_businesses.py` para validar los vectores de ataque y el flujo de login bajo rol `app_api`.
- **Compatibilidad y Riesgos**: Cambio incremental sobre esquema sin datos productivos mediante nueva migración Alembic reversible (`upgrade`/`downgrade`) sin modificar migraciones previas; el backend deberá fijar `SET LOCAL app.current_user_id` en login/onboarding.
- **Non-goals**:
  - Renombrar `app.current_business_id` a `app.tenant_id` (descartado por Opción A).
  - Validación IANA de `timezone` en Pydantic (hallazgo medio #5 de `capa:backend`, diferido a `#39`).
  - Implementación de endpoints FastAPI (`#39`) o tablas de catálogo/ventas (`#42`, `#46`).

## Capabilities

### New Capabilities
*(Ninguna)*

### Modified Capabilities
- `businesses-schema-and-rls`: Incorpora `UNIQUE (user_id)` en `business_users`, políticas RLS granulares con `app.current_user_id` + `app.current_business_id`, y control DCL para el rol runtime `app_api`.

## Impact

- **Migraciones Alembic**: Nueva revisión incremental en `backend/migrations/versions/` (revisando `c843e91d84f1`).
- **Modelos ORM**: Sincronización de `UniqueConstraint` en `backend/app/modules/auth/models.py` (requerido por `uv run alembic check` en CI).
- **Suite de Tests**: Nuevos casos adversariales en `backend/tests/integration/test_db_businesses.py`.
- **Desbloqueo**: Desbloquea el merge de `#39` (PR `#52`).
