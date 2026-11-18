# Proposal: Endurecimiento RLS, DCL y Rol Runtime (`issue-54-hardening-auth-rls-db`)

## Why
La auditoría red-team sobre el PR #52 (issue #54) identificó brechas críticas de seguridad en la capa de base de datos:
1. `businesses_onboarding_insert` tiene `WITH CHECK (true)` y `authenticated` conserva `GRANT ALL` (incluyendo `TRUNCATE`, que omite RLS).
2. `business_users_insert_own_user` permite `app.current_business_id IS NULL`, habilitando la inserción de membresías en comercios ajenos desde cualquier sesión solo-usuario.
3. El runtime conecta como `postgres` (`BYPASSRLS` / `CREATEROLE`), generando una arquitectura fail-open si un endpoint omite `SET LOCAL ROLE app_api` o ejecuta queries tras un `commit()`.
4. Falta distinción de `role` en `UPDATE`/`DELETE` de `business_users` y automatización de `updated_at` en `businesses`.

## What
- Nueva migración Alembic (`forward` + `downgrade` simétrico) que:
  - Restringe `businesses_onboarding_insert` exigiendo `app.current_user_id` no nulo e `id = app.current_business_id`.
  - Revoca todos los privilegios sobre `businesses` y `business_users` de `PUBLIC`, `anon` y `authenticated`.
  - Endurece `business_users_insert_own_user` exigiendo `app.current_business_id` seteado y coincidente con `business_id`.
  - Incorpora guarda de rol (`app.current_user_role = 'owner'` cuando esté presente) en `business_users_update_isolation` y `business_users_delete_isolation`.
  - Provisiona el rol runtime `app_runtime` (`LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE`) miembro de `app_api`.
  - Agrega trigger `BEFORE UPDATE` para mantener `businesses.updated_at`.
- Ampliación de la suite de integración DB-TDD en `backend/tests/integration/test_db_businesses.py`.

## Non-goals
- Cambios en endpoints FastAPI, manejo de errores HTTP o cliente `httpx` (cubiertos en `issue-54-hardening-auth-rls-backend`).
- Implementación de `/refresh`, `/logout` o `/me` (hallazgo 9, diferido).
- Soporte multi-comercio por usuario (`uq_business_users_user_id` se mantiene).

## Compatibility
- 100% compatible con el flujo de onboarding existente (`AuthRepository.create_business_with_owner` ya fija `app.current_user_id` y `app.current_business_id` antes de insertar).
- Migración reversible mediante `alembic downgrade -1`.
