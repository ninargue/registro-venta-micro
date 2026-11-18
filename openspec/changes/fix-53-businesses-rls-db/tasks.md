## 1. Suite de Tests DB-TDD Adversariales en ROJO

- [ ] 1.1 Agregar pruebas de unicidad (`UNIQUE (user_id)`) en `backend/tests/integration/test_db_businesses.py` verificando rechazo (`23505`) al asociar un mismo usuario a un segundo comercio
- [ ] 1.2 Agregar pruebas de login y aislamiento de lectura RLS (`SELECT`) en `business_users` usando `SET LOCAL app.current_user_id` bajo rol `app_api` (resolviendo el deadlock sin `app.current_business_id` y bloqueando lectura cruzada de otros usuarios)
- [ ] 1.3 Agregar pruebas adversariales de `INSERT` y `UPDATE` RLS en `business_users` bajo rol `app_api` (rechazo `42501` ante `user_id` ajeno, sin `app.current_user_id`, `business_id` inconsistente con sesión activa o intento de cambio de `business_id` en `UPDATE`)
- [ ] 1.4 Agregar pruebas DCL/RLS para verificar que `app_api` existe con `rolsuper = false` y `rolbypassrls = false`, no es dueño de tablas, opera CRUD bajo RLS y carece de privilegio `TRUNCATE`
- [ ] 1.5 Ejecutar `cd backend && uv run pytest tests/integration/test_db_businesses.py` contra `DB_TEST_URL` y confirmar el fallo inicial en ROJO de los nuevos escenarios

## 2. Sincronización ORM y Migración DDL/Índices

- [ ] 2.1 Agregar `UniqueConstraint("user_id", name="uq_business_users_user_id")` en `BusinessUser.__table_args__` dentro de `backend/app/modules/auth/models.py`
- [ ] 2.2 Crear nueva migración Alembic incremental en `backend/migrations/versions/` con `down_revision = "c843e91d84f1"` (sin modificar migraciones existentes)
- [ ] 2.3 Implementar en `upgrade()` la sustitución del índice `ix_business_users_user_id` por la restricción `uq_business_users_user_id` (`UNIQUE (user_id)`) sobre `business_users`

## 3. Seguridad RLS Granular, DCL (`app_api`) y Reversibilidad

- [ ] 3.1 Reemplazar en `upgrade()` las políticas previas `business_users_tenant_isolation` y `business_users_onboarding_insert` por políticas granulares en `business_users`: `business_users_select_isolation` (`app.current_business_id` OR `app.current_user_id`), `business_users_insert_own_user` (`user_id = current_user_id` y consistencia con `current_business_id` si está fijado), `business_users_update_isolation` (`USING` + `WITH CHECK`) y `business_users_delete_isolation`
- [ ] 3.2 Provisionar de forma idempotente en `upgrade()` el rol `app_api` (`NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS`) y otorgar `GRANT USAGE ON SCHEMA public TO app_api;` y `GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE ... TO app_api;` en sentencias independientes para `businesses` y `business_users`
- [ ] 3.3 Implementar `downgrade()` simétrico completo revocando permisos de `app_api` sobre `business_users` y `businesses`, restaurando las políticas RLS de `c843e91d84f1` y revirtiendo `uq_business_users_user_id` a `ix_business_users_user_id`

## 4. Verificación en VERDE, Integridad Alembic y Gates

- [ ] 4.1 Aplicar migraciones (`cd backend && uv run alembic upgrade head`) contra `DB_TEST_URL` y validar sincronía ORM (`uv run alembic check`) y reversibilidad (`uv run alembic downgrade -1` / `downgrade base` y `upgrade head`)
- [ ] 4.2 Ejecutar validación estática SQL (`validate-db-migrations.js`), chequeos de calidad (`uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy app`) y suite completa `uv run pytest` confirmando 100% en VERDE
