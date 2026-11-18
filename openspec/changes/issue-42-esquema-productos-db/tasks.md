## 1. Suite DB-TDD en ROJO

- [x] 1.1 Crear `backend/tests/integration/test_db_products.py` con pruebas de estructura y precisión decimal (`numeric(12,2)` en `sale_price`, `cost_price`, `stock`, ausencia de `float`/`real`/`double precision`, defaults y `NOT NULL`)
- [x] 1.2 Agregar en `backend/tests/integration/test_db_products.py` pruebas de integridad y reglas de dominio (`FK -> businesses(id) ON DELETE CASCADE`, `CHECK`s de `name`/`code`/`sale_price > 0`/`cost_price >= 0`, saldo negativo permitido en `stock` tras decremento atómico, unicidad parcial de `(business_id, code) WHERE code IS NOT NULL`, `is_active` y trigger `updated_at`)
- [x] 1.3 Agregar pruebas adversariales de RLS y DCL en `backend/tests/integration/test_db_products.py` (`ENABLE` + `FORCE ROW LEVEL SECURITY`, aislamiento por `app.current_business_id` en `SELECT`/`INSERT`/`UPDATE`/`DELETE` bajo `app_api` y `app_runtime`, rechazo `42501` en escritura cross-tenant o sin contexto, verificación de no-propiedad/no-bypass y bloqueo `42501` de `TRUNCATE` y acceso para `PUBLIC`/`anon`/`authenticated`)
- [x] 1.4 Ejecutar `cd backend && uv run pytest tests/integration/test_db_products.py` contra `DB_TEST_URL` y confirmar el fallo inicial en ROJO antes de implementar DDL

## 2. Modelo ORM SQLAlchemy y Migración DDL/Índices/Triggers

- [x] 2.1 Definir el modelo `Product` en `backend/app/modules/catalog/models.py` (usando `Decimal` y `Numeric(12, 2)`, constraints e índices alineados) y registrarlo en `backend/app/db/base.py`
- [x] 2.2 Crear nueva migración Alembic incremental en `backend/migrations/versions/` con `down_revision = "f8b2c1a94d07"` (sin modificar migraciones existentes) creando la tabla `products` con `pk_products`, `fk_products_business_id` (`ON DELETE CASCADE`), `uq_products_business_id_id` y constraints `CHECK`
- [x] 2.3 Implementar en `upgrade()` el índice único parcial `uq_products_business_id_code` (`WHERE code IS NOT NULL`), el índice compuesto `ix_products_business_id_active_name` (`business_id, is_active, name`), la función `public.set_products_updated_at()` (`clock_timestamp()`) y el trigger `trg_products_set_updated_at` (`BEFORE UPDATE`)

## 3. Seguridad RLS Granular, Privilegios DCL y Reversibilidad

- [ ] 3.1 Habilitar y forzar RLS en `products` (`ENABLE` y `FORCE ROW LEVEL SECURITY`) y crear las 4 políticas granulares (`products_select_isolation`, `products_insert_isolation`, `products_update_isolation` con `USING` + `WITH CHECK`, y `products_delete_isolation`) filtradas por `app.current_business_id`
- [ ] 3.2 Configurar sentencias DCL en `upgrade()`: `REVOKE ALL ON TABLE products FROM PUBLIC, anon, authenticated;` y `GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE products TO app_api;` (sin `TRUNCATE`)
- [ ] 3.3 Implementar `downgrade()` simétrico completo revocando permisos de `app_api`, eliminando las 4 políticas RLS, deshabilitando RLS, eliminando `trg_products_set_updated_at` y `public.set_products_updated_at()`, eliminando índices y ejecutando `op.drop_table("products")`

## 4. Verificación en VERDE, Integridad Alembic y Mutation Testing

- [ ] 4.1 Ejecutar validación estática SQL (`validate-db-migrations.js`), aplicar `cd backend && uv run alembic upgrade head`, comprobar sincronía ORM (`uv run alembic check`) y validar roundtrip (`alembic downgrade -1` / `downgrade base` y `upgrade head`) contra `DB_TEST_URL`
- [ ] 4.2 Ejecutar `cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy app` y `cd backend && uv run pytest` confirmando 100% en VERDE
- [ ] 4.3 Auditar falsabilidad de `backend/tests/integration/test_db_products.py` (Mutation Testing de constraints y RLS) y confirmar `openspec validate "issue-42-esquema-productos-db"` en verde
