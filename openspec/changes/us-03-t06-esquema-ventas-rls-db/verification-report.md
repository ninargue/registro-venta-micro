# Verification Report: `us-03-t06-esquema-ventas-rls-db`

**Fecha:** 2026-11-19  
**Cambio:** `us-03-t06-esquema-ventas-rls-db` (US-03-T06 / Issue `#46` — Tablas `sales`, `sale_items` y `payments`, idempotencia `(business_id, client_id)`, FKs compuestas y RLS/DCL)  
**Revisión Alembic:** `d4e7f1a2b9c3` (descendiente de `a3f9d2e1b4c8`)  
**Auditor:** Principal Database QA & Adversarial Reviewer (`opsx:verify` — Paso 5.4)  
**Dictamen Mecánico (`scripts/db-verify-gate.js`):** **`[APROBADO]`**

---

## Scorecard de Auditoría Cualitativa (`opsx:verify`)

| Dimensión | Estado | Puntuación | Resumen |
|---|---|---|---|
| **Completeness** | PASS | 100% | 5/5 Requirements y 19/19 Scenarios de `spec.md` implementados y cubiertos por 21 tests en `backend/tests/integration/test_db_sales.py`. Tareas `1.1`–`4.2` completadas (`4.3` reservada para Paso 6 Mutation Testing). `openspec validate "us-03-t06-esquema-ventas-rls-db"` válido. |
| **Correctness** | PASS | 100% | Precisión estricta `numeric(12,2)` (sin `float`), 17 constraints (`PK`, `FK` simples/compuestas con `ON DELETE CASCADE`/`RESTRICT`, `UK`s, `CHECK`s), 4 índices explícitos liderados por `business_id`, `ENABLE`+`FORCE ROW LEVEL SECURITY` con 12 políticas granulares y DCL mínimo privilegio. `114 passed` en `pytest`, `ruff check`, `ruff format --check` y `mypy app` en verde. |
| **Coherence** | PASS | 100% | Drift Check 1:1 de `design.md` contra migración `20261119_0006-d4e7f1a2b9c3`, modelos ORM (`Sale`, `SaleItem`, `Payment` en `backend/app/modules/sales/models.py` registrados en `backend/app/db/base.py`), `docs/04-modelo-de-datos/erd.md` y catálogos en vivo de `postgres_test`. `alembic check` sin operaciones pendientes. |

**Hallazgos bloqueantes:** `0` Críticos, `0` Altos, `0` Medios (`1` observación informativa no bloqueante).

---

## Dictamen Adjunto de `scripts/db-verify-gate.js`

- **Resultado global:** **`[APROBADO]`**
- **`validate-db-migrations`:** `exit 0`
- **`db-roundtrip`:** `exit 0`
- **`db-test-fingerprint`:** `exit 0`
- **`test-suite`:** `exit 0` (`114 passed` en ejecución completa de `uv run pytest`, 100% cobertura en `app/modules/sales/models.py`)
- **Calidad estática y sincronía ORM:**
  - `uv run alembic check`: `No new upgrade operations detected.` (`exit 0`)
  - `uv run ruff check .`: `All checks passed!` (`exit 0`)
  - `uv run ruff format --check .`: `41 files already formatted` (`exit 0`)
  - `uv run mypy app`: `Success: no issues found in 27 source files` (`exit 0`)

---

## Matriz de Trazabilidad (Spec ↔ DDL/ORM ↔ Tests)

| Requirement (`spec.md`) | Implementación DDL / ORM | Cobertura en `backend/tests/integration/test_db_sales.py` |
|---|---|---|
| **Req 1:** `sales` — estructura, `numeric(12,2)`, `uq_sales_business_id_id`, idempotencia `uq_sales_business_id_client_id`, FK `ON DELETE CASCADE` | `20261119_0006-d4e7f1a2b9c3` + `Sale` (`sales/models.py:24-52`) | `test_insert_sale_valid_with_defaults`, `test_insert_sale_rejects_nulls_on_mandatory_attributes`, `test_sales_rejects_zero_or_negative_total_amount`, `test_sales_duplicate_client_id_within_business_supports_idempotency`, `test_sales_same_client_id_allowed_across_distinct_businesses`, `test_sales_rejects_orphan_business_and_cascades_on_business_delete` |
| **Req 2:** `sale_items` — snapshots congelados (`unit_price`, `unit_cost`), `numeric(12,2)`, FKs compuestas `ON DELETE CASCADE` (sales) y `ON DELETE RESTRICT` (products) | `20261119_0006-d4e7f1a2b9c3` + `SaleItem` (`sales/models.py:55-99`) | `test_sale_item_freezes_unit_price_and_unit_cost_after_product_edit`, `test_sales_exact_decimal_precision_without_float`, `test_sale_items_rejects_nulls_and_invalid_numeric_bounds`, `test_sale_items_composite_fks_reject_cross_business_references`, `test_sale_items_restricts_product_delete_and_cascades_on_sale_delete` |
| **Req 3:** `payments` — métodos `'cash'`, `'card'`, `'transfer'`, `amount > 0`, FK compuesta `ON DELETE CASCADE` | `20261119_0006-d4e7f1a2b9c3` + `Payment` (`sales/models.py:102-139`) | `test_payments_multiple_valid_methods_persisted_for_sale`, `test_payments_rejects_invalid_method_non_positive_amount_and_nulls`, `test_payments_rejects_cross_business_sale_and_cascades_on_sale_delete` |
| **Req 4:** RLS forzada granular (`SELECT`, `INSERT`, `UPDATE` con `USING`+`WITH CHECK`, `DELETE`) por `app.current_business_id` | `ENABLE` + `FORCE ROW LEVEL SECURITY` y 12 políticas `*_isolation` en `sales`, `sale_items`, `payments` | `test_rls_authorized_tenant_dml_and_idempotent_retry_under_app_runtime`, `test_rls_cross_tenant_select_update_delete_blocked_across_sales_tables`, `test_rls_cross_tenant_insert_and_update_hijack_rejected`, `test_rls_without_tenant_context_returns_empty_and_blocks_writes` |
| **Req 5:** DCL mínimo privilegio y no-bypass (`REVOKE ALL` a `PUBLIC/anon/authenticated`, DML exclusivo a `app_api`/`app_runtime` sin `TRUNCATE`) | `REVOKE ALL` + `GRANT SELECT, INSERT, UPDATE, DELETE TO app_api` | `test_sales_metadata_forced_rls_non_privileged_ownership_and_grants`, `test_app_runtime_cannot_truncate_sales_tables`, `test_authenticated_and_anon_cannot_access_or_truncate_sales_tables` |

---

## Evidencia contra la base

Inspección directa ejecutada sobre la base efímera PostgreSQL 17 (`127.0.0.1:54422/postgres_test`) en revisión `d4e7f1a2b9c3`:

### 1. `information_schema.columns` (`sales`, `sale_items`, `payments`)

| Tabla | Columna | `data_type` (`udt_name`) | Precisión / Longitud | `is_nullable` | `column_default` | Match `design.md` |
|---|---|---|---|---|---|---|
| `sales` | `id` | `uuid` (`uuid`) | - | `NO` | `gen_random_uuid()` | OK |
| `sales` | `business_id` | `uuid` (`uuid`) | - | `NO` | `null` | OK |
| `sales` | `client_id` | `uuid` (`uuid`) | - | `NO` | `null` | OK |
| `sales` | `total_amount` | `numeric` (`numeric`) | `(12, 2)` | `NO` | `null` | OK |
| `sales` | `created_at` | `timestamp with time zone` (`timestamptz`) | - | `NO` | `now()` | OK |
| `sale_items` | `id` | `uuid` (`uuid`) | - | `NO` | `gen_random_uuid()` | OK |
| `sale_items` | `business_id` | `uuid` (`uuid`) | - | `NO` | `null` | OK |
| `sale_items` | `sale_id` | `uuid` (`uuid`) | - | `NO` | `null` | OK |
| `sale_items` | `product_id` | `uuid` (`uuid`) | - | `NO` | `null` | OK |
| `sale_items` | `quantity` | `numeric` (`numeric`) | `(12, 2)` | `NO` | `null` | OK |
| `sale_items` | `unit_price` | `numeric` (`numeric`) | `(12, 2)` | `NO` | `null` | OK |
| `sale_items` | `unit_cost` | `numeric` (`numeric`) | `(12, 2)` | `NO` | `null` | OK |
| `sale_items` | `created_at` | `timestamp with time zone` (`timestamptz`) | - | `NO` | `now()` | OK |
| `payments` | `id` | `uuid` (`uuid`) | - | `NO` | `gen_random_uuid()` | OK |
| `payments` | `business_id` | `uuid` (`uuid`) | - | `NO` | `null` | OK |
| `payments` | `sale_id` | `uuid` (`uuid`) | - | `NO` | `null` | OK |
| `payments` | `payment_method` | `character varying` (`varchar`) | `20` | `NO` | `null` | OK |
| `payments` | `amount` | `numeric` (`numeric`) | `(12, 2)` | `NO` | `null` | OK |
| `payments` | `created_at` | `timestamp with time zone` (`timestamptz`) | - | `NO` | `now()` | OK |

### 2. `pg_constraint` y `pg_indexes`

- **Constraints `sales`:** `pk_sales` (`PRIMARY KEY (id)`), `fk_sales_business_id` (`FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE`), `uq_sales_business_id_id` (`UNIQUE (business_id, id)`), `uq_sales_business_id_client_id` (`UNIQUE (business_id, client_id)`), `chk_sales_total_amount_positive` (`CHECK ((total_amount > (0)::numeric))`).
- **Constraints `sale_items`:** `pk_sale_items` (`PRIMARY KEY (id)`), `fk_sale_items_business_id` (`FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE`), `fk_sale_items_sale` (`FOREIGN KEY (business_id, sale_id) REFERENCES sales(business_id, id) ON DELETE CASCADE`), `fk_sale_items_product` (`FOREIGN KEY (business_id, product_id) REFERENCES products(business_id, id) ON DELETE RESTRICT`), `chk_sale_items_quantity_positive` (`CHECK ((quantity > (0)::numeric))`), `chk_sale_items_unit_price_positive` (`CHECK ((unit_price > (0)::numeric))`), `chk_sale_items_unit_cost_non_negative` (`CHECK ((unit_cost >= (0)::numeric))`).
- **Constraints `payments`:** `pk_payments` (`PRIMARY KEY (id)`), `fk_payments_business_id` (`FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE`), `fk_payments_sale` (`FOREIGN KEY (business_id, sale_id) REFERENCES sales(business_id, id) ON DELETE CASCADE`), `chk_payments_method_valid` (`CHECK (((payment_method)::text = ANY ((ARRAY['cash'::character varying, 'card'::character varying, 'transfer'::character varying])::text[])))`), `chk_payments_amount_positive` (`CHECK ((amount > (0)::numeric))`).
- **Índices (`pg_indexes`):**
  - `sales`: `pk_sales`, `uq_sales_business_id_id`, `uq_sales_business_id_client_id`, `ix_sales_business_id_created_at` (`btree (business_id, created_at)`).
  - `sale_items`: `pk_sale_items`, `ix_sale_items_business_id_sale_id` (`btree (business_id, sale_id)`), `ix_sale_items_business_id_product_id` (`btree (business_id, product_id)`).
  - `payments`: `pk_payments`, `ix_payments_business_id_sale_id` (`btree (business_id, sale_id)`).

### 3. `pg_class`, `pg_policies`, `role_table_grants` y `pg_roles`

- **`pg_class`:** `sales`, `sale_items` y `payments` reportan `relrowsecurity = true`, `relforcerowsecurity = true`, `owner = postgres`.
- **`pg_policies` (12 políticas `PERMISSIVE`):** 4 por tabla (`*_select_isolation`, `*_insert_isolation`, `*_update_isolation` con `qual` y `with_check`, `*_delete_isolation`) evaluando `(business_id = (NULLIF(current_setting('app.current_business_id'::text, true), ''::text))::uuid)`.
- **`information_schema.role_table_grants` y `pg_roles`:**
  - `app_api` (`rolsuper=false`, `rolbypassrls=false`, `rolcanlogin=false`): únicamente `{SELECT, INSERT, UPDATE, DELETE}` sobre las 3 tablas (sin `TRUNCATE`).
  - `app_runtime` (`rolsuper=false`, `rolbypassrls=false`, `rolcanlogin=true`): hereda privilegios de `app_api`.
  - `PUBLIC`, `anon`, `authenticated`: `0` privilegios otorgados.

### 4. Planes `EXPLAIN` (con `SET LOCAL enable_seqscan = off` sobre tabla vacía)

1. **Búsqueda por idempotencia (`WHERE business_id = ... AND client_id = ...`):**
   - `Index Scan using ix_sales_business_id_created_at on sales (cost=0.14..8.16 rows=1)` con `Filter: (client_id = ...)`. *(Nota informativa: en tabla vacía con 0 páginas, PostgreSQL asigna el mismo costo mínimo de 1 página a los índices de `sales`; con datos reales y `ANALYZE`, `uq_sales_business_id_client_id` discrimina directamente en O(log N) y gobierna `ON CONFLICT (business_id, client_id) DO NOTHING`).*
2. **Listado de ventas por fecha (`WHERE business_id = ... ORDER BY created_at DESC`):**
   - `Index Scan Backward using ix_sales_business_id_created_at on sales (cost=0.14..8.16 rows=1)` — sin nodo `Sort` adicional.
3. **Ítems de venta (`WHERE business_id = ... AND sale_id = ...`):**
   - `Index Scan using ix_sale_items_business_id_sale_id on sale_items (cost=0.15..8.17 rows=1)`.
4. **Pagos de venta (`WHERE business_id = ... AND sale_id = ...`):**
   - `Index Scan using ix_payments_business_id_sale_id on payments (cost=0.14..8.16 rows=1)`.

---

## Punto ciego

- **Validación cruzada de totales y descuento de stock:** Por alcance explícito de `Non-Goals` (`design.md` y `proposal.md`), la consistencia `SUM(payments.amount) == sales.total_amount` y la deducción atómica `products.stock = products.stock - quantity` residen en el servicio transaccional (`#47` / `TICKET-07`), no en triggers diferidos de BD.
- **Estadísticas vacías en `postgres_test`:** Los planes `EXPLAIN` se evaluaron sobre tablas vacías (`est_rows = 0 / -1`) forzando `enable_seqscan = off`.
- **Falsabilidad de tests (`4.3`):** La auditoría de Mutation Testing (M1–M5) sobre `backend/tests/integration/test_db_sales.py` queda pendiente para el Paso 6 del ciclo `db-sdd`.

---

## Veredicto

**`APROBADO`** — `0` hallazgos críticos/altos/medios; implementación completa, correcta y coherente con `spec.md`, `design.md` y los catálogos reales de PostgreSQL 17. Listo para Paso 6 (Mutation Testing).
