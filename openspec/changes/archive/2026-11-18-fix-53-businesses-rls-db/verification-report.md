# Verification Report — `fix-53-businesses-rls-db`

- **Cambio:** `fix-53-businesses-rls-db` (Issue #53, bloqueante de #39 / PR #52)
- **Fecha de verificación:** `2026-11-17`
- **Veredicto del gate determinista (`db-verify-gate.js`):** **`[APROBADO]`** (`validate-db-migrations`, `db-roundtrip`, `db-test-fingerprint`, `test-suite` y `typecheck` en `exit 0`)

---

## Scorecard (`opsx:verify`)

| Dimensión | Estado | Cobertura / Resultado | Hallazgos |
|---|---|---|---|
| **Completeness** | ✅ PASS | `13/13` tareas `- [x]` en `tasks.md`; `3/3` requirements de `specs/` implementados | 0 CRITICAL, 0 WARNING |
| **Correctness** | ✅ PASS | `20/20` tests en VERDE (`uv run pytest -v`), incluyendo 12 nuevos escenarios DB-TDD adversariales de RLS, DCL y `UNIQUE (user_id)` | 0 CRITICAL, 0 WARNING |
| **Coherence** | ✅ PASS | Drift Check 1:1 entre `design.md`, `models.py`, migración `0003` e `information_schema` / `pg_policies` / `pg_indexes` / `pg_roles`; `alembic check` limpio | 0 CRITICAL, 0 WARNING |
| **Quality & Types** | ✅ PASS | `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy app` (18 archivos) en `exit 0` | 0 CRITICAL, 0 WARNING |

---

## 1. Completeness

- **`tasks.md`:** `13/13` tareas completadas (`- [x]`).
- **`openspec status --change "fix-53-businesses-rls-db" --json`:** `isComplete: true` (`proposal`, `design`, `specs`, `tasks` en `done`).
- **Requisitos de `specs/businesses-schema-and-rls/spec.md`:**
  1. **Business Users Association and Role Assignment:** PK compuesta `(business_id, user_id)`, FK `ON DELETE CASCADE`, `CHECK (role IN ('owner', 'cashier'))`, y nueva restricción `uq_business_users_user_id` (`UNIQUE (user_id)`) implementada en `20261117_0003-e4a7c2b91f03_fix_businesses_rls_and_unique_user.py` y `backend/app/modules/auth/models.py`.
  2. **Row-Level Security Isolation via Session Context:** `ENABLE` + `FORCE ROW LEVEL SECURITY` en `businesses` y `business_users`, con políticas granulares en `business_users` (`business_users_select_isolation`, `business_users_insert_own_user`, `business_users_update_isolation`, `business_users_delete_isolation`) usando `app.current_business_id` y `app.current_user_id`.
  3. **Runtime Role Privileges and RLS Non-Bypass Guarantees:** Rol `app_api` provisionado idempotente (`NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS`) con `GRANT USAGE ON SCHEMA public TO app_api;` y `GRANT SELECT, INSERT, UPDATE, DELETE` independientes sobre `businesses` y `business_users` (sin `TRUNCATE`).

---

## 2. Correctness (Matriz de Trazabilidad Specs ↔ Tests)

Ejecución observada: `cd backend && uv run pytest -v` → **`20 passed in 27.92s`** (`0 failed`, `0 skipped`).

| Scenario (`spec.md`) | Test (`backend/tests/integration/test_db_businesses.py`) | Resultado |
|---|---|---|
| Successful association of user to business | `test_business_users_membership_and_valid_role` | ✅ PASSED |
| Rejection of invalid user roles | `test_business_users_rejects_invalid_role` | ✅ PASSED |
| Cascade deletion on business removal | `test_business_users_cascade_delete` | ✅ PASSED |
| Rejection of duplicate business membership for the same user (`23505`) | `test_business_users_rejects_duplicate_user_id` | ✅ PASSED |
| Tenant reads own business data / Cross-tenant blocked / Empty without context | `test_rls_isolation_by_session_variable`, `test_rls_business_users_select_by_business_id` | ✅ PASSED |
| User resolves own membership during login using `app.current_user_id` | `test_rls_business_users_login_select_by_current_user_id` | ✅ PASSED |
| Cross-user membership read blocked when only `app.current_user_id` is set | `test_rls_business_users_cross_user_select_blocked` | ✅ PASSED |
| Authenticated user inserts own membership during onboarding | `test_rls_business_users_insert_own_user_allowed` | ✅ PASSED |
| Impersonated insert for another `user_id` rejected by RLS (`42501`) | `test_rls_business_users_insert_impersonated_user_rejected` | ✅ PASSED |
| Unauthenticated insert without user context rejected by RLS (`42501`) | `test_rls_business_users_insert_without_user_context_rejected` | ✅ PASSED |
| Cross-tenant insert when active `business_id` mismatches rejected by RLS (`42501`) | `test_rls_business_users_insert_mismatched_business_id_rejected` | ✅ PASSED |
| Cross-tenant update hijack on `business_users` rejected by RLS (`42501`) | `test_rls_business_users_update_hijack_rejected` | ✅ PASSED |
| Runtime role `app_api` has no RLS bypass or table ownership privileges | `test_app_api_role_exists_without_bypass_or_ownership` | ✅ PASSED |
| Runtime role `app_api` performs permitted operations under RLS context | `test_app_api_performs_permitted_dml_under_rls` | ✅ PASSED |
| Runtime role `app_api` cannot bypass RLS on cross-tenant rows or truncate tables | `test_app_api_cannot_bypass_rls_or_truncate` | ✅ PASSED |

---

## 3. Coherence (Drift Check & Integridad)

- **Sincronía ORM vs Migraciones:** `uv run alembic check` → `No new upgrade operations detected.` (`exit 0`). `BusinessUser.__table_args__` en `backend/app/modules/auth/models.py` declara `UniqueConstraint("user_id", name="uq_business_users_user_id")` en coincidencia exacta con `0003`.
- **Migraciones previas intactas:** `20261102_0001-ba617f3a8caa_baseline.py` y `20261116_0002-c843e91d84f1_create_businesses_and_rls.py` no fueron modificadas; `0003` encadena `down_revision = "c843e91d84f1"` con `downgrade()` simétrico verificado por `db-roundtrip`.
- **Lint & Typecheck:** `uv run ruff check .` (`All checks passed!`), `uv run ruff format --check .` (`25 files already formatted`), `uv run mypy app` (`Success: no issues found in 18 source files`).

---

## Evidencia contra la base

Consultas ejecutadas directamente contra la base PostgreSQL local migrada a `e4a7c2b91f03`:

### 1. Columnas (`information_schema.columns`)
- `businesses`: `id` (`uuid`, `NO`, `gen_random_uuid()`), `name` (`character varying`, `NO`), `country` (`character varying`, `NO`), `timezone` (`character varying`, `NO`), `created_at` (`timestamp with time zone`, `NO`, `now()`), `updated_at` (`timestamp with time zone`, `NO`, `now()`).
- `business_users`: `business_id` (`uuid`, `NO`), `user_id` (`uuid`, `NO`), `role` (`character varying`, `NO`), `created_at` (`timestamp with time zone`, `NO`, `now()`).

### 2. Políticas RLS (`pg_policies`)
- `business_users`:
  - `business_users_select_isolation` (`SELECT`): `((business_id = (NULLIF(current_setting('app.current_business_id'::text, true), ''::text))::uuid) OR (user_id = (NULLIF(current_setting('app.current_user_id'::text, true), ''::text))::uuid))`
  - `business_users_insert_own_user` (`INSERT`): `WITH CHECK ((user_id = (NULLIF(current_setting('app.current_user_id'::text, true), ''::text))::uuid) AND (((NULLIF(current_setting('app.current_business_id'::text, true), ''::text))::uuid IS NULL) OR (business_id = (NULLIF(current_setting('app.current_business_id'::text, true), ''::text))::uuid)))`
  - `business_users_update_isolation` (`UPDATE`): `USING` y `WITH CHECK` `(business_id = (NULLIF(current_setting('app.current_business_id'::text, true), ''::text))::uuid)`
  - `business_users_delete_isolation` (`DELETE`): `(business_id = (NULLIF(current_setting('app.current_business_id'::text, true), ''::text))::uuid)`
- `businesses`:
  - `businesses_tenant_isolation` (`ALL`) y `businesses_onboarding_insert` (`INSERT`, `WITH CHECK true`).

### 3. Índices (`pg_indexes`)
- `businesses`: `pk_businesses` (`UNIQUE BTREE (id)`).
- `business_users`: `pk_business_users` (`UNIQUE BTREE (business_id, user_id)`), `uq_business_users_user_id` (`UNIQUE BTREE (user_id)`). El índice no único previo `ix_business_users_user_id` fue reemplazado sin duplicidad.

### 4. Rol y Privilegios (`pg_roles` / `information_schema.role_table_grants`)
- `pg_roles`: `app_api` con `rolsuper = False`, `rolbypassrls = False`, `rolcreaterole = False`, `rolcreatedb = False`, `rolcanlogin = False`.
- `role_table_grants` para `app_api`: únicamente `SELECT`, `INSERT`, `UPDATE`, `DELETE` sobre `businesses` y `business_users` (sin `TRUNCATE`).

### 5. Planes de Ejecución (`EXPLAIN (COSTS OFF)` bajo `SET LOCAL ROLE app_api`)
- **Login lookup por `user_id`** (con `enable_seqscan = off` para validar uso de índice en tabla vacía):
  ```text
  Index Scan using uq_business_users_user_id on business_users
    Index Cond: (user_id = '00000000-0000-0000-0000-000000000001'::uuid)
    Filter: ((business_id = (NULLIF(current_setting('app.current_business_id'::text, true), ''::text))::uuid) OR (user_id = (NULLIF(current_setting('app.current_user_id'::text, true), ''::text))::uuid))
  ```
- **Tenant lookup por `business_id`** (con `enable_seqscan = off`):
  ```text
  Index Scan using pk_business_users on business_users
    Index Cond: (business_id = '00000000-0000-0000-0000-000000000002'::uuid)
    Filter: ((business_id = (NULLIF(current_setting('app.current_business_id'::text, true), ''::text))::uuid) OR (user_id = (NULLIF(current_setting('app.current_user_id'::text, true), ''::text))::uuid))
  ```
  *(Nota: con `enable_seqscan = on` sobre una tabla con 0 filas en entorno de pruebas, el planificador elige `Seq Scan` por costo mínimo trivial).*

---

## Punto ciego

1. **Política `businesses_onboarding_insert` (`FOR INSERT WITH CHECK (true)`):** Conforme al alcance acotado de `#53` (`design.md`), se mantiene abierta para `INSERT` en `businesses`. Un proceso con `app_api` sin contexto podría insertar un comercio huérfano (aunque no puede leerlo ni vincularlo en `business_users` sin `app.current_user_id`). Además, el contrato de onboarding en `#39` requiere que la transacción fije `SET LOCAL app.current_business_id` antes de ejecutar `INSERT INTO businesses ... RETURNING ...`.
2. **Validación IANA de `timezone`:** Diferida a la capa Pydantic/API en `#39`; la base valida únicamente `VARCHAR(50) NOT NULL`.
3. **Datos productivos:** La base local de verificación está vacía (greenfield); los planes `EXPLAIN` con `Index Scan` se validaron forzando `enable_seqscan = off`.

---

## Dictamen Final

- **Gate determinista (`db-verify-gate.js`):** **`[APROBADO]`**
- **Auditoría cualitativa (`opsx:verify`):** **`PASS`** — Listo para archivar (`opsx:archive`) y continuar con la capa backend (`#39`).
