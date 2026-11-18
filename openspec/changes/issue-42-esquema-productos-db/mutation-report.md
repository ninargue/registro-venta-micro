# 🔬 REPORTE DE MUTATION TESTING Y FALSABILIDAD: issue-42-esquema-productos-db

## 1. Veredicto de Falsabilidad
- **Estado:** `[TESTS COMPLACIENTES DETECTADOS]`
- **Tests Auditados:** `backend/tests/integration/test_db_products.py` (20 tests de integración DB — `20 passed` en corridas consecutivas sobre `postgresql+asyncpg://postgres:postgres@127.0.0.1:54422/postgres`)
- **Tasa de Mutantes Eliminados:** `28/32` (`87.5%`)

> Todas las mutaciones fueron ejecutadas contra PostgreSQL 17 local (`postgresql+asyncpg://postgres:postgres@127.0.0.1:54422/postgres`) dentro de transacciones efímeras con `ROLLBACK` completo (savepoints por test + rollback externo de cada mutación). Conteo verificado antes y después de la auditoría y tras dos ejecuciones completas de `pytest`: `businesses = 62`, `business_users = 26`, `products = 0`, y las 7 constraints en `pg_constraint` intactas sin mutaciones ni filas residuales.

---

## 2. Matriz de Mutaciones Evaluadas

| ID | Mutación | Archivo de Test | ¿Atrapó el Fallo? | Resultado |
|---|---|---|---|---|
| M1a | Omitir `UNIQUE (business_id, id)` (`ALTER TABLE products DROP CONSTRAINT uq_products_business_id_id`) | `backend/tests/integration/test_db_products.py` (20/20 tests pasaron) | No | 🧟 Vivo |
| M1b | Omitir `PRIMARY KEY (id)` (`ALTER TABLE products DROP CONSTRAINT pk_products`) | `backend/tests/integration/test_db_products.py` (20/20 tests pasaron) | No | 🧟 Vivo |
| M1c | Omitir índice único parcial `uq_products_business_id_code` (`DROP INDEX uq_products_business_id_code`) | `backend/tests/integration/test_db_products.py::test_products_rejects_duplicate_non_null_code_in_same_business` (`DID NOT RAISE IntegrityError`) | Sí | 🗑 Eliminado |
| M1d | Reemplazar `uq_products_business_id_code` por unicidad global `(code) WHERE code IS NOT NULL` sin `business_id` | `backend/tests/integration/test_db_products.py::test_products_allows_same_code_across_distinct_businesses` (`23505 UniqueViolationError`) | Sí | 🗑 Eliminado |
| M1e | Reemplazar `uq_products_business_id_code` por `UNIQUE NULLS NOT DISTINCT (business_id, code)` | `backend/tests/integration/test_db_products.py::test_products_allows_multiple_null_codes_in_same_business` (`23505 UniqueViolationError`) | Sí | 🗑 Eliminado |
| M1f | Convertir `uq_products_business_id_code` en `UNIQUE (business_id, code)` completo sin predicado parcial `WHERE code IS NOT NULL` | `backend/tests/integration/test_db_products.py` (20/20 tests pasaron; DML equivalente en PG17 con `NULLS DISTINCT`, sin validar `pg_index.indpred`) | No | 🧟 Vivo |
| M1g | Omitir o quitar `trim()` en `chk_products_name_not_empty` (`char_length(trim(name)) > 0`) | `backend/tests/integration/test_db_products.py::test_products_rejects_blank_name_or_blank_non_null_code` (`DID NOT RAISE IntegrityError`) | Sí | 🗑 Eliminado |
| M1h | Omitir o quitar `trim()` en `chk_products_code_not_empty` (`code IS NULL OR char_length(trim(code)) > 0`) | `backend/tests/integration/test_db_products.py::test_products_rejects_blank_name_or_blank_non_null_code` (`DID NOT RAISE IntegrityError`) | Sí | 🗑 Eliminado |
| M1i | Omitir o relajar (`>= 0`) `chk_products_sale_price_positive` (`sale_price > 0`) | `backend/tests/integration/test_db_products.py::test_products_rejects_zero_or_negative_sale_price` (`DID NOT RAISE IntegrityError`) | Sí | 🗑 Eliminado |
| M1j | Omitir o sobre-restringir (`> 0`) `chk_products_cost_price_non_negative` (`cost_price >= 0`) | `backend/tests/integration/test_db_products.py::test_products_rejects_negative_cost_price_allows_zero`, `test_insert_product_valid_with_defaults` | Sí | 🗑 Eliminado |
| M1k | Agregar `CHECK (stock >= 0)` prohibido en `products` (rompe saldo negativo transitorio US-03) | `backend/tests/integration/test_db_products.py::test_products_atomic_stock_deduction_allows_transient_negative` (`23514 CheckViolationError`) | Sí | 🗑 Eliminado |
| M1l | Omitir `NOT NULL` en `business_id`, `name`, `sale_price`, `cost_price`, `stock` o `is_active` | `backend/tests/integration/test_db_products.py::test_insert_product_rejects_nulls_on_mandatory_attributes` (6/6 columnas atrapadas con `23502`) | Sí | 🗑 Eliminado |
| M1m | Omitir `NOT NULL` en columnas de auditoría (`created_at`, `updated_at`) | `backend/tests/integration/test_db_products.py` (20/20 tests pasaron) | No | 🧟 Vivo |
| M1n | Cambiar `sale_price` / `cost_price` / `stock` de `numeric(12,2)` a `double precision` o `numeric(12,3)` | `backend/tests/integration/test_db_products.py::test_products_exact_decimal_precision_without_float`, `test_insert_product_valid_with_defaults` | Sí | 🗑 Eliminado |
| M1o | Omitir trigger `trg_products_set_updated_at` o usar `now()` en vez de `clock_timestamp()` | `backend/tests/integration/test_db_products.py::test_products_soft_deactivation_preserves_row_and_advances_updated_at` (`ts_1 > ts_0` falla) | Sí | 🗑 Eliminado |
| M1p | Omitir o alterar `DEFAULT` en `id`, `cost_price`, `stock`, `is_active`, `created_at` o `updated_at` | `backend/tests/integration/test_db_products.py::test_insert_product_valid_with_defaults`, `test_app_runtime_cannot_truncate_products` | Sí | 🗑 Eliminado |
| M2a | Omitir FK `fk_products_business_id` e insertar `business_id` huérfano | `backend/tests/integration/test_db_products.py::test_insert_product_rejects_orphan_business_id`, `test_products_cascade_delete_when_business_removed` | Sí | 🗑 Eliminado |
| M2b | Cambiar `ON DELETE CASCADE` a `ON DELETE NO ACTION` en `fk_products_business_id` | `backend/tests/integration/test_db_products.py::test_products_cascade_delete_when_business_removed` (`23503 ForeignKeyViolationError`) | Sí | 🗑 Eliminado |
| M3a | Deshabilitar RLS (`ALTER TABLE products DISABLE ROW LEVEL SECURITY`) | `backend/tests/integration/test_db_products.py::test_products_metadata_forced_rls_and_non_privileged_ownership`, `test_rls_products_cross_tenant_insert_and_update_hijack_rejected` | Sí | 🗑 Eliminado |
| M3b | Desactivar `FORCE ROW LEVEL SECURITY` (`ALTER TABLE products NO FORCE ROW LEVEL SECURITY`) | `backend/tests/integration/test_db_products.py::test_products_metadata_forced_rls_and_non_privileged_ownership` (`relforcerowsecurity is True` falla) | Sí | 🗑 Eliminado |
| M3c | Omitir (`DROP POLICY`) o relajar a `USING (true)` la política `products_select_isolation` | `backend/tests/integration/test_db_products.py::test_rls_products_authorized_tenant_crud_under_app_runtime`, `test_rls_products_cross_tenant_select_update_delete_blocked`, `test_rls_products_without_tenant_context_returns_empty_and_blocks_insert` | Sí | 🗑 Eliminado |
| M3d | Omitir (`DROP POLICY`) o relajar a `WITH CHECK (true)` la política `products_insert_isolation` | `backend/tests/integration/test_db_products.py::test_rls_products_authorized_tenant_crud_under_app_runtime`, `test_rls_products_cross_tenant_insert_and_update_hijack_rejected`, `test_rls_products_without_tenant_context_returns_empty_and_blocks_insert` | Sí | 🗑 Eliminado |
| M3e | Omitir (`DROP POLICY`) o relajar `USING`/`WITH CHECK` a `true` en `products_update_isolation` | `backend/tests/integration/test_db_products.py::test_rls_products_authorized_tenant_crud_under_app_runtime`, `test_rls_products_cross_tenant_insert_and_update_hijack_rejected`, `test_rls_products_without_tenant_context_returns_empty_and_blocks_insert` | Sí | 🗑 Eliminado |
| M3f | Omitir (`DROP POLICY`) o relajar a `USING (true)` la política `products_delete_isolation` | `backend/tests/integration/test_db_products.py::test_rls_products_authorized_tenant_crud_under_app_runtime`, `test_rls_products_cross_tenant_select_update_delete_blocked`, `test_rls_products_without_tenant_context_returns_empty_and_blocks_insert` | Sí | 🗑 Eliminado |
| M3g | Otorgar `BYPASSRLS` a `app_runtime` o `app_api` (`ALTER ROLE ... BYPASSRLS`) | `backend/tests/integration/test_db_products.py::test_products_metadata_forced_rls_and_non_privileged_ownership`, `test_rls_products_cross_tenant_insert_and_update_hijack_rejected` | Sí | 🗑 Eliminado |
| M3h | Asignar propiedad de `products` a `app_api` (`ALTER TABLE products OWNER TO app_api`) | `backend/tests/integration/test_db_products.py::test_products_metadata_forced_rls_and_non_privileged_ownership`, `test_app_runtime_cannot_truncate_products` | Sí | 🗑 Eliminado |
| M3i | Otorgar `TRUNCATE` o `REFERENCES` sobre `products` a `app_api` | `backend/tests/integration/test_db_products.py::test_app_runtime_cannot_truncate_products`, `test_products_metadata_forced_rls_and_non_privileged_ownership` | Sí | 🗑 Eliminado |
| M3j | Otorgar `SELECT` (o DML) sobre `products` a `PUBLIC`, `anon` o `authenticated` | `backend/tests/integration/test_db_products.py::test_authenticated_and_anon_cannot_access_or_truncate_products`, `test_products_metadata_forced_rls_and_non_privileged_ownership` | Sí | 🗑 Eliminado |
| M3k | Omitir `NULLIF(..., '')` o `missing_ok=true` en `current_setting('app.current_business_id', true)` | `backend/tests/integration/test_db_products.py::test_rls_products_without_tenant_context_returns_empty_and_blocks_insert` (atrapa `22P02 != 42501`; en conexión nueva `NullPool` atrapa `42704`) | Sí | 🗑 Eliminado |
| M4a | Enmascarar `SQLSTATE` de constraint (trigger con `ERRCODE = 'P0001'` en vez de `23514`) | `backend/tests/integration/test_db_products.py::test_products_rejects_zero_or_negative_sale_price` (`_assert_sqlstate` exige `23514`) | Sí | 🗑 Eliminado |
| M4b | Enmascarar `SQLSTATE` de RLS (`22P02` en vez de `42501`) | `backend/tests/integration/test_db_products.py::_assert_sqlstate(..., "42501")` en todos los tests RLS/DCL | Sí | 🗑 Eliminado |
| M5 | Fuga de datos sin `ROLLBACK` o falta de idempotencia entre ejecuciones | `backend/tests/integration/test_db_products.py` (2 ejecuciones consecutivas `20 passed`; filas antes/después: `businesses=62, business_users=26, products=0`) | Sí | 🗑 Eliminado |

*(Nota informativa fuera del catálogo de constraints/RLS: la eliminación del índice de rendimiento `ix_products_business_id_active_name` tampoco rompe tests funcionales en tablas vacías, lo cual es esperado porque es un índice B-tree no único y ya fue verificado vía `EXPLAIN` en `verification-report.md`.)*

---

## 3. Brechas de Falsabilidad y Acción Requerida

Se detectaron **4 mutantes sobrevivientes en la categoría M1 (Constraint Deletion)** en `backend/tests/integration/test_db_products.py`, mientras que **M2 (Orphan FK / Cascade)**, **M3 (RLS Bypass / DCL)**, **M4 (Masked SQLSTATE)** y **M5 (Rollback Isolation)** están **100% blindados**.

### Brechas detectadas que requieren refuerzo por `db-qa-agent`

1. **`M1a` — Eliminación de `uq_products_business_id_id` (`UNIQUE (business_id, id)`) [CRÍTICO para `spec.md` / `#46`]:**
   - **Evidencia:** Ejecutar `ALTER TABLE products DROP CONSTRAINT uq_products_business_id_id;` dentro de una transacción efímera deja los 20 tests de `test_db_products.py` en verde (`20/20 PASSED`).
   - **Por qué importa:** `spec.md` (`Requirement: Products Table Structure...`) y `design.md` exigen explícitamente la clave única compuesta `uq_products_business_id_id` sobre `(business_id, id)` para habilitar futuras FKs compuestas tenant-safe desde `sale_items` (`Issue #46`). Sin prueba que la valide, la omisión de `uq_products_business_id_id` pasaría inadvertida hasta fallar en `#46`.
   - **Acción requerida:** Agregar aserción en `backend/tests/integration/test_db_products.py` que verifique la existencia efectiva de la constraint `UNIQUE (business_id, id)` (`uq_products_business_id_id`) — idealmente probando en transacción efímera con `ROLLBACK` la creación de una tabla temporal hija con `FOREIGN KEY (business_id, product_id) REFERENCES products(business_id, id)` (falla con `42830` si falta `uq_products_business_id_id`) y comprobando su registro en `pg_constraint`.

2. **`M1b` — Eliminación de `pk_products` (`PRIMARY KEY (id)`) [ALTO]:**
   - **Evidencia:** Ejecutar `ALTER TABLE products DROP CONSTRAINT pk_products;` deja los 20 tests en verde (`20/20 PASSED`), porque `test_insert_product_valid_with_defaults` solo comprueba que `id` omitido genera un UUID, sin probar rechazo de `id` duplicado (`23505`).
   - **Acción requerida:** Agregar prueba negativa insertando dos filas en `products` con el mismo `id` explícito dentro de savepoint y verificando `_assert_sqlstate(exc, "23505")` (y/o verificar `contype = 'p'` en `pg_constraint`).

3. **`M1m` — Eliminación de `NOT NULL` en `created_at` y `updated_at` [MEDIO]:**
   - **Evidencia:** `test_insert_product_rejects_nulls_on_mandatory_attributes` valida `NOT NULL` (`23502`) en las 6 columnas operativas (`business_id`, `name`, `sale_price`, `cost_price`, `stock`, `is_active`), pero no intenta insertar `NULL` explícito en `created_at` o `updated_at` (`spec.md` exige `timestamptz NOT NULL DEFAULT now()`).
   - **Acción requerida:** Ampliar `null_cases` en `test_insert_product_rejects_nulls_on_mandatory_attributes` para incluir `created_at = NULL` y `updated_at = NULL` esperando `IntegrityError` con SQLSTATE `23502`.

4. **`M1f` — Degradación de índice parcial `uq_products_business_id_code` a `UNIQUE (business_id, code)` sin predicado `WHERE code IS NOT NULL` [MENOR / Estructural]:**
   - **Evidencia:** En PostgreSQL 17, `UNIQUE (business_id, code)` sin `NULLS NOT DISTINCT` tiene comportamiento DML equivalente (`NULL` repetido permitido, no-nulos únicos), por lo que la prueba funcional no distingue el predicado parcial exigido por `spec.md` (`only where code IS NOT NULL`).
   - **Acción requerida:** Verificar en `pg_indexes` / `pg_index` (`indpred IS NOT NULL` / `WHERE (code IS NOT NULL)`) que `uq_products_business_id_code` sea efectivamente un índice único parcial sobre `(business_id, code)`.

### Siguiente paso sugerido
Re-despachar a `db-qa-agent` para reforzar `backend/tests/integration/test_db_products.py` con las 4 aserciones faltantes (`M1a`, `M1b`, `M1m`, `M1f`), ejecutar `db-test-fingerprint.js --action refreeze --reason "Refuerzo de aserciones tras Mutation Testing"`, re-ejecutar `pytest` y re-auditar en Paso 6 hasta alcanzar `[TESTS BLINDADOS]` antes de marcar la tarea `4.3` en `tasks.md`.
