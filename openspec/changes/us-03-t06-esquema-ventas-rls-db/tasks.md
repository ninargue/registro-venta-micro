## 1. Suite DB-TDD en ROJO

- [ ] 1.1 Crear `backend/tests/integration/test_db_sales.py` con pruebas de estructura, defaults (`gen_random_uuid()`, `now()`), nulabilidad (`23502`) y precisión decimal exacta (`numeric(12,2)` en `sales.total_amount`, `sale_items.quantity`, `sale_items.unit_price`, `sale_items.unit_cost` y `payments.amount`, sin `float`/`real`/`double precision`)
- [ ] 1.2 Agregar en `backend/tests/integration/test_db_sales.py` pruebas de idempotencia y reglas de dominio (`uq_sales_business_id_client_id` rechazando duplicado directo con `23505`, `INSERT ... ON CONFLICT (business_id, client_id) DO NOTHING` conservando 1 fila, mismo `client_id` permitido en comercios distintos, snapshots congelados de `unit_price`/`unit_cost` tras editar `products`, FKs compuestas `(business_id, sale_id)` y `(business_id, product_id)` rechazando cruces cross-tenant con `23503`, `ON DELETE RESTRICT` en `products`, `ON DELETE CASCADE` desde `sales` y `businesses`, y todos los `CHECK`s incluyendo `payment_method IN ('cash', 'card', 'transfer')`)
- [ ] 1.3 Agregar pruebas adversariales de RLS y DCL en `backend/tests/integration/test_db_sales.py` (`ENABLE` + `FORCE ROW LEVEL SECURITY` en `sales`, `sale_items` y `payments`, aislamiento por `app.current_business_id` en `SELECT`/`INSERT`/`UPDATE`/`DELETE` bajo `app_runtime`, rechazo `42501` en escritura cross-tenant incluyendo `ON CONFLICT DO NOTHING` y acceso sin contexto, verificación de no-propiedad/no-bypass en catálogos `pg_*`, y bloqueo `42501` de `TRUNCATE` y acceso para `PUBLIC`/`anon`/`authenticated`)
- [ ] 1.4 Ejecutar `cd backend && uv run pytest tests/integration/test_db_sales.py` contra `DB_TEST_URL` y confirmar el fallo inicial en ROJO antes de implementar ORM y DDL

## 2. Modelos ORM SQLAlchemy y Migración DDL/Índices

- [ ] 2.1 Definir los modelos `Sale`, `SaleItem` y `Payment` en `backend/app/modules/sales/models.py` (usando `Decimal`, `Numeric(12, 2)`, FKs compuestas, constraints e índices idénticos al diccionario físico) y registrarlos en `backend/app/db/base.py`
- [ ] 2.2 Crear nueva migración Alembic incremental en `backend/migrations/versions/` con `down_revision = "a3f9d2e1b4c8"` (sin modificar migraciones existentes) creando primero la tabla padre `sales` (`pk_sales`, `fk_sales_business_id` `ON DELETE CASCADE`, `uq_sales_business_id_id`, `uq_sales_business_id_client_id`, `chk_sales_total_amount_positive`)
- [ ] 2.3 Crear en `upgrade()` las tablas hijo `sale_items` (`pk_sale_items`, `fk_sale_items_business_id`, `fk_sale_items_sale` `ON DELETE CASCADE`, `fk_sale_items_product` `ON DELETE RESTRICT`, `CHECK`s de `quantity > 0`, `unit_price > 0`, `unit_cost >= 0`) y `payments` (`pk_payments`, `fk_payments_business_id`, `fk_payments_sale` `ON DELETE CASCADE`, `CHECK`s de `payment_method` y `amount > 0`)
- [ ] 2.4 Crear en `upgrade()` los índices B-tree liderados por `business_id`: `ix_sales_business_id_created_at`, `ix_sale_items_business_id_sale_id`, `ix_sale_items_business_id_product_id` e `ix_payments_business_id_sale_id`

## 3. Seguridad RLS Granular, Privilegios DCL y Reversibilidad

- [ ] 3.1 Habilitar y forzar RLS (`ENABLE` y `FORCE ROW LEVEL SECURITY`) en `sales`, `sale_items` y `payments`, y crear las 12 políticas granulares (`SELECT`, `INSERT`, `UPDATE` con `USING` + `WITH CHECK`, y `DELETE` por cada tabla) filtradas por `NULLIF(current_setting('app.current_business_id', true), '')::uuid`
- [ ] 3.2 Configurar sentencias DCL independientes en `upgrade()`: `REVOKE ALL` desde `PUBLIC, anon, authenticated` y `GRANT SELECT, INSERT, UPDATE, DELETE ... TO app_api;` (sin `TRUNCATE`) para `sales`, `sale_items` y `payments`
- [ ] 3.3 Implementar `downgrade()` simétrico completo en orden inverso (`payments` → `sale_items` → `sales`): revocando permisos de `app_api`, eliminando las 12 políticas RLS, deshabilitando/quitando force RLS, eliminando índices y ejecutando `op.drop_table(...)`
- [ ] 3.4 Actualizar la referencia de revisión Alembic `head` en `docs/04-modelo-de-datos/erd.md` tras generar la migración definitiva

## 4. Verificación en VERDE, Integridad Alembic y Mutation Testing

- [ ] 4.1 Ejecutar validación estática SQL (`validate-db-migrations.js`), aplicar `cd backend && uv run alembic upgrade head`, comprobar sincronía ORM (`uv run alembic check`) y validar roundtrip (`alembic downgrade -1` / `downgrade base` y `upgrade head`) contra `DB_TEST_URL`
- [ ] 4.2 Ejecutar `cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy app` y `cd backend && uv run pytest` confirmando 100% en VERDE
- [ ] 4.3 Auditar falsabilidad de `backend/tests/integration/test_db_sales.py` (Mutation Testing M1–M5 sobre constraints, FKs compuestas, idempotencia y RLS) y confirmar `openspec validate "us-03-t06-esquema-ventas-rls-db"` en verde
