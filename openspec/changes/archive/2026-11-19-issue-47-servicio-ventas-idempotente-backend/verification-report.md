# Verification Report — `issue-47-servicio-ventas-idempotente-backend`

**Veredicto:** `[APROBADO]`  
**Fecha:** 2026-11-19  
**Worktree:** `C:\Users\Armenta\Documents\Repositories\wt-47-servicio-ventas-idempotente`  
**Cambio OpenSpec:** `issue-47-servicio-ventas-idempotente-backend` (Issue #47 / `US-03-T07`)

---

## 1. Scorecard `opsx:verify`

| Dimensión | Estado | Resumen |
|---|---|---|
| **Completeness** | PASS (con observación menor en `tasks.md`) | Todos los artefactos de implementación (`core/schemas.py`, `catalog/*`, `sales/*`, `main.py`, `docs/api/openapi.json`) y la cobertura funcional de los escenarios de `specs/sales-api/spec.md` están completos. Las tareas `5.1`–`5.3` figuran sin marcar `[ ]` en `tasks.md` y las pruebas de esquemas/integración se consolidaron en `backend/tests/integration/test_sales_api.py` (en lugar de `test_sales_schemas.py` y `test_sales.py`). |
| **Correctness** | PASS | Drift Check 1:1 aprobado contra `design.md` y `docs/api/openapi.json` (`export_openapi --check` en verde). Los 17 escenarios de `specs/sales-api/spec.md` (los 16 escenarios funcionales/contrato + el escenario de formato uniforme `ErrorResponse`) tienen correspondencia verificada en `backend/tests/integration/test_sales_api.py`. |
| **Coherence** | PASS | Arquitectura `Router → Service → Repository` respetada; frontera modular `SalesService → CatalogService` sobre la misma `AsyncSession` transaccional (`get_tenant_db`). Auditoría RLS/RBAC/IDOR limpia: `SET LOCAL ROLE app_api` + `app.current_business_id` desde JWT, sin bypass ni uso de `service_role`. |

---

## 2. Matriz de Gates 1–4 y Comandos Verificados

| Gate / Check | Fuente | Resultado | Evidencia |
|---|---|---|---|
| **Gate 1–3 (Pre-checks & Seguridad)** | Reportado por orquestador | PASS (con aviso informativo) | Aviso informativo preexistente sobre mención a `service_role` en `backend/app/core/config.py`; auditado abajo (solo comentario prohibitivo, sin credencial ni bypass). 0 cambios en `backend/migrations/`. |
| **Gate 4 (`pytest`)** | Reportado por orquestador | PASS (`242 passed`) | `uv run pytest --no-cov -q` -> `242 passed`; huella de tests congelados verificada en 11 archivos. *(Nota: en la shell aislada de este subagente no existe `backend/.env`, por lo que `pytest` requiere las variables de entorno de BD del entorno del orquestador).* |
| **OpenAPI Drift Check** | Ejecutado en Fase B | PASS (exit 0) | `uv run --directory backend python -m app.scripts.export_openapi --check` -> `OK: ...\docs\api\openapi.json coincide con el esquema OpenAPI actual de FastAPI.` |
| **Lint (`ruff check`)** | Ejecutado en Fase B | PASS (exit 0) | `uv run --directory backend ruff check .` -> `All checks passed!` |
| **Format (`ruff format`)** | Ejecutado en Fase B | PASS (exit 0) | `uv run --directory backend ruff format --check .` -> `55 files already formatted` |
| **Typecheck (`mypy`)** | Ejecutado en Fase B | PASS (exit 0) | `uv run --directory backend mypy app` -> `Success: no issues found in 37 source files` |

---

## 3. Auditoría de Seguridad (RLS / RBAC / IDOR / Anti-Bypass)

- **`rls_mode = "in-situ"`**:
  - `POST /api/v1/sales` (`backend/app/modules/sales/router.py`) inyecta `current_user: CurrentUser = Depends(get_current_tenant)` y `service: SalesService = Depends(get_sales_service)` donde `get_sales_service` depende de `get_tenant_db` (`backend/app/core/db.py`).
  - `get_tenant_db` abre la transacción con `NullPool` y ejecuta `SET LOCAL ROLE app_api`, `set_config('app.current_user_id', ...)` y `set_config('app.current_business_id', ...)` usando exclusivamente el `CurrentUser` del JWT.
  - `SalesService.create_sale` toma `business_id = current_user.business_id` del JWT y `SaleCreate` configura `model_config = ConfigDict(extra="ignore")`, ignorando cualquier `business_id` enviado en el payload.
- **Auditoría de `service_role` en `backend/app/core/config.py`**:
  - En `backend/app/core/config.py:23` únicamente existe el comentario `# Supabase Auth (prohibido usar service_role en flujos de usuario).`. No existe ningún campo `service_role` en `Settings` ni referencia en `backend/app/modules/sales/`. El flujo de ventas no elude RLS ni usa roles privilegiados.
- **Aislamiento cruzado y RBAC**:
  - Roles autorizados: `owner` y `cashier` (`get_current_tenant`), omitiendo `unit_cost` en `SaleItemResponse` (`sale_items.unit_cost` queda congelado solo en BD).
  - Productos inexistentes o de otro negocio responden `404 PRODUCT_NOT_FOUND` bajo RLS sin revelar existencia ni modificar el stock del otro tenant.
  - El mismo `client_id` UUID se permite de forma independiente entre negocios distintos (`uq_sales_business_id_client_id`).

---

## 4. Mapa `Scenario -> test` (`specs/sales-api/spec.md` -> `backend/tests/integration/test_sales_api.py`)

> `specs/sales-api/spec.md` contiene **17 escenarios** en total (16 escenarios específicos de operación/validación/seguridad/OpenAPI + 1 escenario transversal de formato uniforme `ErrorResponse`). Todos están cubiertos en `backend/tests/integration/test_sales_api.py`:

| # | Escenario en `specs/sales-api/spec.md` | Test(s) en `backend/tests/integration/test_sales_api.py` | Estado |
|---|---|---|---|
| 1 | Successful sale registration with single payment method and frozen snapshots | `test_create_sale_single_payment_and_frozen_snapshots` (L199) | Cubierto |
| 2 | Successful sale registration with combined payment methods and exact decimal sum | `test_create_sale_combined_payments_exact_decimal_sum` (L317) | Cubierto |
| 3 | Fractional quantity rounding and duplicate product lines aggregate stock deduction cleanly | `test_fractional_quantity_rounding_and_duplicate_product_lines` (L397) | Cubierto |
| 4 | Counter sale succeeds when stock becomes negative | `test_counter_sale_succeeds_when_stock_becomes_negative` (L468) | Cubierto |
| 5 | Transactional rollback restores database state on mid-transaction failure | `test_transactional_rollback_on_mid_transaction_failure` (L539) | Cubierto |
| 6 | Sequential retry with identical client_id returns 200 without duplicating records or re-deducting stock | `test_sequential_idempotent_retry_returns_200_even_after_catalog_change` (L597) | Cubierto |
| 7 | Concurrent retries with identical client_id produce a single sale and single stock deduction | `test_concurrent_idempotent_retries_deduct_stock_once` (L675) | Cubierto |
| 8 | Same client_id allowed across distinct businesses without cross-tenant collision | `test_same_client_id_allowed_across_distinct_businesses` (L743) | Cubierto |
| 9 | Rejection of payment total mismatch against server-calculated sale total | `test_reject_payment_total_mismatch` (L808) | Cubierto |
| 10 | Rejection of inactive product for new sale creation | `test_reject_inactive_product_for_new_sale` (L864) | Cubierto |
| 11 | Rejection of float values, excessive decimal places, non-positive amounts, and overflow | `test_reject_float_bool_nonfinite_scale_nonpositive_and_overflow` (L940) + `test_reject_sale_total_rounding_to_zero_or_overflow` (L971) | Cubierto |
| 12 | Rejection of empty items, empty payments, invalid payment method, invalid UUID, or NUL bytes | `test_reject_empty_lists_invalid_method_invalid_uuid_or_nul_bytes` (L1084) | Cubierto |
| 13 | Unauthenticated or onboarding-pending requests rejected with 401 and 403 | `test_unauthenticated_and_onboarding_pending_rejected` (L1106) | Cubierto |
| 14 | Both owner and cashier roles authorized to register sales without exposing unit_cost | `test_owner_and_cashier_authorized_without_exposing_unit_cost` (L1131) | Cubierto |
| 15 | Cross-tenant or non-existent product rejected with 404 and body business_id ignored | `test_cross_tenant_or_missing_product_rejected_404_and_body_business_id_ignored` (L1179) | Cubierto |
| 16 | Sales route and schemas documented in OpenAPI schema | `test_openapi_documents_sales_routes_and_schemas` (L1269) | Cubierto |
| 17 | All sales error responses conform to uniform ErrorResponse format | Verificado transversalmente con `_assert_uniform_error_response` (L184) en todos los tests de error `401`, `403`, `404` y `422` (L842, L898, L966, L1022, L1023, L1101, L1124, L1125, L1242, L1243) | Cubierto |

---

## 5. Observaciones sobre `tasks.md` (Solo Documentación)

- En `openspec/changes/issue-47-servicio-ventas-idempotente-backend/tasks.md`, las tareas `1.1`–`4.2` están marcadas `[x]`, mientras que `5.1`, `5.2` y `5.3` permanecen `[ ]`.
- Las pruebas unitarias de validación de esquemas y contrato (`5.1`) y las pruebas de integración/RLS (`5.2`) fueron consolidadas en la suite congelada `backend/tests/integration/test_sales_api.py` (en lugar de `backend/tests/unit/test_sales_schemas.py` y `backend/tests/integration/test_sales.py`), cubriendo todos los casos exigidos y pasando Gate 4 (`242 passed`).
- Esta diferencia organizativa de archivos de test y el estado `[ ]` de `5.1`–`5.3` en `tasks.md` quedan documentados sin bloquear la aprobación funcional ni de seguridad del cambio.
