# Verification Report: `issue-42-esquema-productos-db`

**Fecha:** 2026-11-18  
**Cambio:** `issue-42-esquema-productos-db` (US-02-T03 / Issue `#42` — Tabla `products`, precisión `numeric(12,2)`, unicidad parcial de `code`, trigger `updated_at` y RLS/DCL)  
**Revisión Alembic:** `a3f9d2e1b4c8` (descendiente de `f8b2c1a94d07`)  
**Auditor:** Principal Database QA & Adversarial Reviewer (`opsx:verify` — Paso 5.4)  
**Dictamen Mecánico (`scripts/db-verify-gate.js`):** **`[APROBADO]`**

---

## Scorecard de Auditoría Cualitativa (`opsx:verify`)

| Dimensión | Estado | Puntuación | Resumen |
|---|---|---|---|
| **Completeness** | PASS | 100% | 6/6 Requirements y 18/18 Scenarios de `spec.md` implementados y cubiertos por 20 tests en `test_db_products.py`. Drift Check 1:1 contra `design.md` sin desviaciones. Tareas `1.1`–`4.2` completadas (`4.3` reservada para Paso 6 Mutation Testing). |
| **Correctness** | PASS | 100% | Tipos `numeric(12,2)` exactos (sin `float`), 7 constraints (`PK`, `FK ON DELETE CASCADE`, `UK`, 4 `CHECK`), 4 índices B-tree (con índice líder en FK), trigger `BEFORE UPDATE` con `clock_timestamp()`, `ENABLE`+`FORCE ROW LEVEL SECURITY`, 4 políticas granulares y DCL mínimo privilegio. |
| **Coherence** | PASS | 100% | Modelo ORM `Product` registrado en `backend/app/db/base.py` sincronizado al 100% con la migración (`alembic check` limpio). `downgrade()` simétrico completo verificado con roundtrip. |

**Hallazgos bloqueantes:** `0` Críticos, `0` Altos, `0` Medios (`2` observaciones informativas no bloqueantes).

---

## Dictamen Adjunto de `scripts/db-verify-gate.js`

- **Resultado global:** **`[APROBADO]`**
- **`validate-db-migrations`:** `exit 0` (14 chequeos superados)
- **`db-roundtrip`:** `exit 0` (`forward-only` idempotente, `up × 2` sin deriva; además `alembic check` sin operaciones pendientes y `downgrade -1` / `upgrade head` superados)
- **`db-test-fingerprint`:** `exit 0` (6 archivos `.py` intactos)
- **`test-suite`:** `exit 0` (`90 passed`)
- **Calidad estática Python:** `ruff check .` y `mypy app` sin errores.

---

## Matriz de Trazabilidad (Spec ↔ DDL/ORM ↔ Tests)

| Requirement / Escenario (`spec.md`) | Implementación DDL / ORM | Cobertura en `backend/tests/integration/test_db_products.py` |
|---|---|---|
| **Req 1:** Estructura `products`, `numeric(12,2)`, FK `ON DELETE CASCADE`, `uq_products_business_id_id` | `20261118_0005-a3f9d2e1b4c8_create_products_table.py` + `Product` (`catalog/models.py`) | `test_insert_product_valid_with_defaults`, `test_products_exact_decimal_precision_without_float`, `test_insert_product_rejects_nulls_on_mandatory_attributes`, `test_insert_product_rejects_orphan_business_id`, `test_products_cascade_delete_when_business_removed` |
| **Req 2:** Check constraints (`name`, `code`, `sale_price > 0`, `cost_price >= 0`) y `stock` negativo transitorio | `chk_products_name_not_empty`, `chk_products_code_not_empty`, `chk_products_sale_price_positive`, `chk_products_cost_price_non_negative` (sin `CHECK` en `stock`) | `test_products_rejects_blank_name_or_blank_non_null_code`, `test_products_rejects_zero_or_negative_sale_price`, `test_products_rejects_negative_cost_price_allows_zero`, `test_products_atomic_stock_deduction_allows_transient_negative` |
| **Req 3:** Unicidad parcial de `(business_id, code) WHERE code IS NOT NULL` | Índice único parcial `uq_products_business_id_code` | `test_products_allows_multiple_null_codes_in_same_business`, `test_products_rejects_duplicate_non_null_code_in_same_business`, `test_products_allows_same_code_across_distinct_businesses` |
| **Req 4:** Baja lógica (`is_active`) y trigger `updated_at` | `is_active DEFAULT true`, `public.set_products_updated_at()` (`clock_timestamp()`), `trg_products_set_updated_at` | `test_products_soft_deactivation_preserves_row_and_advances_updated_at` |
| **Req 5:** RLS forzada granular en `SELECT`/`INSERT`/`UPDATE`/`DELETE` | `ENABLE` + `FORCE ROW LEVEL SECURITY` y 4 políticas `products_*_isolation` (`USING` / `WITH CHECK`) | `test_rls_products_authorized_tenant_crud_under_app_runtime`, `test_rls_products_cross_tenant_select_update_delete_blocked`, `test_rls_products_cross_tenant_insert_and_update_hijack_rejected`, `test_rls_products_without_tenant_context_returns_empty_and_blocks_insert` |
| **Req 6:** DCL mínimo privilegio y no-bypass | `REVOKE ALL` a `PUBLIC, anon, authenticated`; `GRANT SELECT, INSERT, UPDATE, DELETE` a `app_api` (heredado por `app_runtime`) | `test_products_metadata_forced_rls_and_non_privileged_ownership`, `test_app_runtime_cannot_truncate_products`, `test_authenticated_and_anon_cannot_access_or_truncate_products` |

---

## Evidencia contra la base

Inspección directa ejecutada sobre PostgreSQL 17 local (`127.0.0.1:54422/postgres`) tras `alembic upgrade head`:

### 1. `information_schema.columns` (`public.products`)

| Columna | `data_type` (`udt_name`) | Precisión / Longitud | `is_nullable` | `column_default` | Match `design.md` |
|---|---|---|---|---|---|
| `id` | `uuid` (`uuid`) | - | `NO` | `gen_random_uuid()` | OK |
| `business_id` | `uuid` (`uuid`) | - | `NO` | `null` | OK |
| `code` | `character varying` (`varchar`) | `50` | `YES` | `null` | OK |
| `name` | `character varying` (`varchar`) | `150` | `NO` | `null` | OK |
| `sale_price` | `numeric` (`numeric`) | `(12, 2)` | `NO` | `null` | OK |
| `cost_price` | `numeric` (`numeric`) | `(12, 2)` | `NO` | `0` | OK |
| `stock` | `numeric` (`numeric`) | `(12, 2)` | `NO` | `0` | OK |
| `is_active` | `boolean` (`bool`) | - | `NO` | `true` | OK |
| `created_at` | `timestamp with time zone` (`timestamptz`) | - | `NO` | `now()` | OK |
| `updated_at` | `timestamp with time zone` (`timestamptz`) | - | `NO` | `now()` | OK |

### 2. `pg_constraint`, `pg_indexes`, `pg_trigger`

- **Constraints (`pg_constraint`):**
  - `pk_products` (`p`): `PRIMARY KEY (id)`
  - `fk_products_business_id` (`f`): `FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE`
  - `uq_products_business_id_id` (`u`): `UNIQUE (business_id, id)`
  - `chk_products_code_not_empty` (`c`): `CHECK (((code IS NULL) OR (char_length(TRIM(BOTH FROM code)) > 0)))`
  - `chk_products_name_not_empty` (`c`): `CHECK ((char_length(TRIM(BOTH FROM name)) > 0))`
  - `chk_products_sale_price_positive` (`c`): `CHECK ((sale_price > (0)::numeric))`
  - `chk_products_cost_price_non_negative` (`c`): `CHECK ((cost_price >= (0)::numeric))`
- **Índices (`pg_indexes`):**
  - `pk_products`: `CREATE UNIQUE INDEX pk_products ON public.products USING btree (id)`
  - `uq_products_business_id_id`: `CREATE UNIQUE INDEX uq_products_business_id_id ON public.products USING btree (business_id, id)`
  - `uq_products_business_id_code`: `CREATE UNIQUE INDEX uq_products_business_id_code ON public.products USING btree (business_id, code) WHERE (code IS NOT NULL)`
  - `ix_products_business_id_active_name`: `CREATE INDEX ix_products_business_id_active_name ON public.products USING btree (business_id, is_active, name)`
- **Trigger y función (`pg_trigger` / `pg_proc`):**
  - `trg_products_set_updated_at` (`tgenabled = 'O'`): `CREATE TRIGGER trg_products_set_updated_at BEFORE UPDATE ON public.products FOR EACH ROW EXECUTE FUNCTION set_products_updated_at()`
  - `public.set_products_updated_at()` (`prosecdef = false`): asigna `NEW.updated_at = clock_timestamp();`.

### 3. `pg_class`, `pg_policies`, `role_table_grants` y `pg_roles`

- **`pg_class`:** `relrowsecurity = true`, `relforcerowsecurity = true`, `owner = postgres`, `est_rows = 0`.
- **`pg_policies` (4 políticas `PERMISSIVE`):**
  - `products_select_isolation` (`SELECT`): `USING (business_id = (NULLIF(current_setting('app.current_business_id'::text, true), ''::text))::uuid)`
  - `products_insert_isolation` (`INSERT`): `WITH CHECK (business_id = (NULLIF(current_setting('app.current_business_id'::text, true), ''::text))::uuid)`
  - `products_update_isolation` (`UPDATE`): `USING (...)` y `WITH CHECK (...)` sobre `app.current_business_id`
  - `products_delete_isolation` (`DELETE`): `USING (...)` sobre `app.current_business_id`
- **Privilegios DCL (`information_schema.role_table_grants` y `pg_roles`):**
  - `app_api`: únicamente `SELECT`, `INSERT`, `UPDATE`, `DELETE` (sin `TRUNCATE`, sin `TRIGGER`, sin `REFERENCES`).
  - `anon` y `authenticated`: `0` privilegios otorgados sobre `products`.
  - `app_api` (`rolsuper=false`, `rolbypassrls=false`, `rolcanlogin=false`) y `app_runtime` (`rolsuper=false`, `rolbypassrls=false`, `rolcanlogin=true`).

### 4. Planes `EXPLAIN` (sin datos sensibles)

1. **Listado de catálogo activo ordenado por nombre** (`WHERE business_id = '<uuid>' AND is_active = true ORDER BY name`):
   - Plan por defecto (`est_rows = 0`): `Sort -> Seq Scan on products` (normal en tabla vacía de 0 páginas).
   - Plan con `SET enable_seqscan = off`:
     ```text
     Index Scan using ix_products_business_id_active_name on products
       Index Cond: ((business_id = '00000000-0000-0000-0000-000000000001'::uuid) AND (is_active = true))
     ```
     Confirma uso directo del índice B-tree compuesto `(business_id, is_active, name)` sin operación `Sort` adicional.
2. **Búsqueda por código** (`WHERE business_id = '<uuid>' AND code = 'SKU-TEST-001'`):
   - Plan por defecto (`est_rows = 0`): `Seq Scan on products`.
   - Plan con `SET enable_seqscan = off`: `Index Scan using ix_products_business_id_active_name on products` (con `Index Cond: business_id = ...` y `Filter: code = 'SKU-TEST-001'`), debido a que con `est_rows = 0` ambos índices B-tree tienen costo estimado idéntico de 1 página; `uq_products_business_id_code` es un índice B-tree parcial válido (`WHERE code IS NOT NULL`) que el optimizador elegirá por selectividad cuando la tabla tenga estadísticas reales de filas.

---

## Hallazgos

1. **[Info] Selección de índice en `EXPLAIN` sobre tabla vacía para `(business_id, code)`:** Con `est_rows = 0` y `enable_seqscan = off`, PostgreSQL empató en costo (1 página) entre `ix_products_business_id_active_name` y `uq_products_business_id_code`. No requiere cambios; en producción con datos y `ANALYZE`, el índice único parcial `uq_products_business_id_code` discrimina por `(business_id, code)`.
2. **[Info] `onupdate=func.now()` en `Product.updated_at` (`models.py`):** SQLAlchemy declara `onupdate=func.now()` mientras el trigger `trg_products_set_updated_at` ejecuta `clock_timestamp()` en `BEFORE UPDATE`. En runtime, el trigger `BEFORE UPDATE` siempre sobreescribe `NEW.updated_at` antes de persistir, garantizando la precisión de `clock_timestamp()`.

---

## Punto ciego

- **Capacidad de rechazo por falsos positivos en tests (`Mutation Testing`):** Esta auditoría verifica la alineación estática y viva entre `spec.md`, `design.md`, la migración Alembic, el modelo ORM y la base PostgreSQL, pero **no muta** todavía las políticas RLS ni los `CHECK` constraints para comprobar que `test_db_products.py` falla ante mutaciones adversariales. Esa verificación corresponde explícitamente al **Paso 6 (Mutation Testing / tarea `4.3`)**.
- **Comportamiento bajo carga real de estadísticas (`ANALYZE`):** Los planes `EXPLAIN` se evaluaron sobre `products` vacía (`est_rows = 0`), requiriendo `enable_seqscan = off` para demostrar la elegibilidad del índice B-tree compuesto.
