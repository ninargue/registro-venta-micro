# Tasks: issue-54-hardening-auth-rls-db

- [x] 1.1 [DB-TDD ROJO] Agregar tests de integración en `backend/tests/integration/test_db_businesses.py` para `businesses_onboarding_insert` sin contexto, `REVOKE ALL` para `authenticated`/`anon`/`PUBLIC`, `business_users_insert_own_user` sin `app.current_business_id`, bloqueo de `UPDATE`/`DELETE` para `cashier`, atributos de `app_runtime`, y trigger `updated_at` en `businesses`; verificar fallo en ROJO.
- [x] 2.1 Crear migración Alembic `backend/migrations/versions/20261118_0004-f8b2c1a94d07_harden_rls_and_runtime_role.py` con `businesses_onboarding_insert` restringido, `REVOKE ALL`, `business_users` RLS endurecido, rol `app_runtime` y trigger `updated_at` (con `downgrade()` simétrico).
- [x] 3.1 Ejecutar `alembic upgrade head`, validar roundtrip (`upgrade` -> `downgrade` -> `upgrade`) y ejecutar suite DB-TDD en VERDE.
