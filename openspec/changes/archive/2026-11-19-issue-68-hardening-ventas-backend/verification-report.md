# Verification Report — `issue-68-hardening-ventas-backend`

- **Cambio OpenSpec:** `issue-68-hardening-ventas-backend` (Issue #68)
- **Worktree:** `C:\Users\Armenta\Documents\Repositories\wt-47-servicio-ventas-idempotente`
- **Fase:** `opsx:verify` (Fase B — Verificación Independiente de Solo Lectura)
- **Veredicto:** **`[APROBADO]`**

---

## 1. Scorecard `opsx:verify`

| Dimensión | Estado | Puntuación | Resumen |
|---|---|---|---|
| **Completeness** (Completitud) | APROBADO | 100% (implementación y tests) | H1, H2, H3 (`409 SALE_ID_CONFLICT`), M1 (`type: "string"` + `409` en `openapi.json`), M2 (`test_sales_schemas.py`), M3 (concurrencia cruzada, límites `500`/`20`, `unit_cost == 0.00`) y M4 (`Product.business_id == business_id` + `UPDATE` masivo `CASE WHEN`) implementados y verificados con tests reales. *(Nota administrativa: las casillas 5.1–5.3 en `tasks.md` permanecen sin marcar `[ ]` aunque el trabajo ya fue ejecutado.)* |
| **Correctness** (Corrección) | APROBADO | 100% | Drift Check 1:1 contra `specs/sales-api/spec.md`, `design.md` y `docs/api/openapi.json` sin desviaciones. Suite completa `276 passed` en PostgreSQL real con RLS `in-situ`. |
| **Coherence** (Coherencia) | APROBADO | 100% | Arquitectura en capas `Router → Service → Repository` preservada, invariante `No-DB-Diff` respetada (`0` cambios en `backend/migrations/`), formato uniforme `ErrorResponse` y cero bypass de RLS/RBAC/IDOR. |

---

## 2. Matriz de Gates 1–4 y Validaciones Fuera de Código

| Gate / Check | Comando ejecutado | Resultado | Evidencia observada |
|---|---|---|---|
| **Gate 1 — Lint & Format** | `uv run --directory backend ruff check .` / `ruff format --check .` | **PASS** | `All checks passed!` / `56 files already formatted` |
| **Gate 2 — Typecheck & OpenAPI** | `uv run --directory backend mypy app` / `python -m app.scripts.export_openapi --check` | **PASS** | `Success: no issues found in 37 source files` / `OK: ...\docs\api\openapi.json coincide con el esquema OpenAPI actual de FastAPI.` |
| **Gate 3 — Seguridad & RLS (`in-situ`)** | Auditoría de código (`backend/app`) + `get_tenant_db` | **PASS** | `get_tenant_db` (`backend/app/core/db.py`) fija `SET LOCAL ROLE app_api`, `app.current_user_id` y `app.current_business_id`. Único match de `service_role` está en comentario prohibitivo (`backend/app/core/config.py:23`). Sin `BYPASSRLS` en `backend/app/`. Aislamiento cross-tenant verificado en tests. |
| **Gate 4 — Suite de Tests** | `uv run pytest --no-cov -q` (con PostgreSQL local `127.0.0.1:54422`) | **PASS** | `276 passed, 156 warnings in 88.59s` (`0` fallos, `0` skipped). Huella de tests congelados y `0` cambios en `backend/migrations/`. |

---

## 3. Auditoría Detallada de Hallazgos (H1–H3, M1–M4)

### H1 — Re-lookup idempotente post-`FOR UPDATE`
- **Implementación:** `SalesService.create_sale` (`backend/app/modules/sales/service.py`, líneas 161–182) ejecuta `lock_products_for_sale` en orden determinista y acto seguido re-ejecuta `self._repository.get_sale_by_client_id(business_id=business_id, client_id=payload.client_id)` antes de validar `missing_ids`, `inactive_ids` o cuadratura financiera.
- **Cobertura:** `test_concurrent_retry_returns_200_when_catalog_changes_before_for_update` (`backend/tests/integration/test_sales_api.py`, líneas 1533–1653) inyecta vía `asyncio.Event` y `before_cursor_execute` la confirmación de la venta original junto con `is_active = false` y cambio de `sale_price` antes de liberar el lock, verificando `200 OK`.

### H2 — Guarda explícita contra overflow `numeric(12,2)` en `stock`
- **Implementación:** `SaleStockOverflowError` (`backend/app/modules/sales/service.py`, líneas 48–49) se lanza cuando `new_deduction > MAX_NUMERIC_12_2` (líneas 209–213) o `resulting_stock < -MAX_NUMERIC_12_2` (líneas 228–233), antes de `PAYMENT_TOTAL_MISMATCH`. Mapeada en `backend/app/modules/sales/router.py` (líneas 102–110) a HTTP `422` (`ErrorResponse(code="VALIDATION_ERROR", details=None)`).
- **Cobertura:** `test_reject_stock_numeric_12_2_overflow_and_allow_min_boundary` (`backend/tests/integration/test_sales_api.py`, líneas 1657–1742) valida rechazo `422 VALIDATION_ERROR` por suma agregada `> 9999999999.99`, rechazo por stock resultante `< -9999999999.99` y aceptación `201 Created` en la frontera exacta `-9999999999.99`.

### H3 — Detección de conflicto `409 SALE_ID_CONFLICT`
- **Implementación:** `SaleIdConflictError` (`backend/app/modules/sales/service.py`, líneas 52–57) y `_assert_idempotent_payload_matches` (líneas 114–135) comparan multiconjuntos ordenados de `(product_id, quantize_decimal(quantity))` y `(payment_method, quantize_decimal(amount))` en los tres puntos de detección: lookup temprano (línea 154), re-lookup post-lock (línea 173) y post-`ON CONFLICT` (línea 284). Mapeada en `router.py` (líneas 93–101) a HTTP `409 Conflict` (`code="SALE_ID_CONFLICT"`, `details={"client_id": str(exc.client_id)}`).
- **Cobertura:** `test_reuse_client_id_with_different_payload_returns_409_conflict`, `test_idempotent_retry_matches_order_independent_multisets_returns_200` y `test_concurrent_client_id_collision_with_different_payloads_returns_201_and_409` (`backend/tests/integration/test_sales_api.py`, líneas 1746–1965).

### M1 — Contrato OpenAPI string-only y estado `409`
- **Implementación:** `DecimalInput` con `WithJsonSchema({"type": "string", "format": "decimal", "pattern": r"^\d{1,10}(\.\d{1,2})?$"})` en `SaleItemCreate.quantity` y `SalePaymentCreate.amount` (`backend/app/modules/sales/schemas.py`, líneas 17–81); `409: {"model": ErrorResponse}` en `router.py` (línea 46).
- **Verificación:** `docs/api/openapi.json` declara `"type": "string"`, `"format": "decimal"`, `"pattern": "^\\d{1,10}(\\.\\d{1,2})?$"` en `SaleItemCreate.quantity` (líneas 976–985) y `SalePaymentCreate.amount` (líneas 1051–1060), y documenta `"409"` en `/api/v1/sales` (líneas 519–528). `export_openapi --check` pasó sin deriva.

### M2 & M3 — Cobertura unitaria, concurrencia cruzada y límites
- **M2 (`backend/tests/unit/test_sales_schemas.py`):** 26 casos unitarios pasando, cubriendo `Decimal` estricto, rechazo de `float`/`bool`/`NaN`/`Infinity`/escala `>2`/overflow/`\x00`, `payment_method`, UUIDs, límites `1..500` y `1..20`, `extra="ignore"` de `business_id`, cuantización sin `unit_cost` y contrato JSON Schema `type: "string"`.
- **M3 (`backend/tests/integration/test_sales_api.py`):** Concurrencia cruzada `[P1, P2]` vs `[P2, P1]` sin deadlocks ni *lost updates* (`test_concurrent_crossed_order_sales_no_deadlocks_or_lost_updates`), límites `500`/`501` ítems y `20`/`21` pagos junto a `unit_cost == 0.00` (`test_items_and_payments_batch_limits_and_zero_unit_cost`).

### M4 — Defense-in-depth y bulk `UPDATE` con `CASE WHEN`
- **Implementación:** `CatalogRepository` (`backend/app/modules/catalog/repository.py`, líneas 91–158) y `CatalogService` (`backend/app/modules/catalog/service.py`, líneas 110–144) exigen `business_id: uuid.UUID` y filtran explícitamente por `Product.business_id == business_id` en `lock_products_for_sale`, `deduct_stock_batch` y `get_product_names_by_ids`. `deduct_stock_batch` ejecuta un único `UPDATE` usando `sqlalchemy.case` y `literal(..., type_=Numeric(12, 2))`.
- **Cobertura:** `test_multi_product_sale_executes_single_tenant_filtered_bulk_update` (`backend/tests/integration/test_sales_api.py`, líneas 2051–2103) verifica exactamente 1 sentencia `update products` con `case` y `business_id`.

---

## 4. Observaciones Menores (No Bloqueantes)

1. **Checklist en `tasks.md`:** Las tareas `5.1`, `5.2` y `5.3` figuran como `- [ ]` en `openspec/changes/issue-68-hardening-ventas-backend/tasks.md` aunque su implementación y ejecución ya fueron completadas y validadas. Se recomienda marcarlas `[x]` antes de archivar el cambio.
