# 🔬 REPORTE DE MUTATION TESTING Y FALSABILIDAD: issue-47-servicio-ventas-idempotente-backend

## 1. Veredicto de Falsabilidad
- **Estado:** `[TESTS COMPLACIENTES DETECTADOS]`
- **Modo de Ejecución:** `Catálogo Canónico M1–M5` (`mutation_cmd: none` en `design.md`; ejecutado sobre copia temporal aislada en `$env:TEMP\mut-sales-47` con `DATABASE_URL=postgresql+asyncpg://postgres:postgres@127.0.0.1:54422/postgres` y el entorno `.venv` de `backend/`. Copia temporal eliminada al finalizar: `TMP_EXISTS=False`; integridad de árbol vivo verificada: `HASH_MISMATCHES=0`, `MUTATION_ARTIFACTS=0`, `47 passed` en `tests/unit`).
- **Tests Auditados:** `backend/tests/integration/test_sales_api.py` (`42 passed` en corrida inicial, con defecto de flakiness detectado en `test_create_sale_combined_payments_exact_decimal_sum`, que falló `5/5` re-ejecuciones aisladas; mutantes evaluados determinísticamente con `-x -k "not test_create_sale_combined_payments_exact_decimal_sum"` sobre los `41` tests restantes) y `backend/tests/integration/test_auth_onboarding.py` (para variantes compartidas de `app/core/security.py` y `app/core/db.py`).
- **Tasa de Mutantes Eliminados:**
  - **Categorías canónicas `M1–M5` totalmente blindadas:** `2/5` en suite completa (`M1`, `M2`; `1/5` estrictamente dentro de `test_sales_api.py`). `M3`, `M4` y `M5` presentan mutantes no equivalentes sobrevivientes.
  - **Variantes discretas no equivalentes:** `49/60` (`81.7%`) eliminadas directamente por `tests/integration/test_sales_api.py`; `51/60` (`85.0%`) eliminadas en el conjunto `backend/tests/` (sumando `M2d_jwt_sig` y `M3e_user_ctx` atrapados por `tests/integration/test_auth_onboarding.py`).
  - **Mutantes sobrevivientes no equivalentes:** `9/60` en toda la suite (`M3f_items_sale_id`, `M3g_payments_sale_id`, `M4b_round_even`, `M4m_subtotal_zero`, `M4o_for_update`, `M4p_order_by_id`, `M4s_items_sort`, `M4t_payments_sort`, `M5m_error_details`), más `2` brechas locales de `test_sales_api.py` cubiertas en `auth` (`M2d_jwt_sig`, `M3e_user_ctx`).
  - **Mutantes equivalentes verificados aparte (excluidos del denominador):** `4` (`M1k_nul`, `M3h_sale_biz_filter`, `M5l_savepoint`, `M5n_no_txn_in_repo`).
  - **Defecto crítico adicional en test existente (Flakiness):** `test_create_sale_combined_payments_exact_decimal_sum` (`test_sales_api.py:372-376`) es no determinista en baseline intacto (`5/5` fallos consecutivos al re-ejecutarlo aislado).

---

## 2. Matriz de Mutaciones Evaluadas

### Resumen Canónico M1–M5

| ID | Mutación | Archivo(s) Mutado(s) (`backend/app`) | Archivo(s) de Test (`backend/tests`) | ¿Atrapó el Fallo? | Resultado |
|---|---|---|---|---|---|
| M1 | Eliminación/relajación de validación de entrada (`Decimal`, `float`, `bool`, `NaN`/`Inf`, `>2` decimales, `gt=0`, overflow `numeric(12,2)`, `min_length`/`max_length` de `items`/`payments`, `PaymentMethod`) | `app/modules/sales/schemas.py`, `app/core/schemas.py` | `tests/integration/test_sales_api.py` | Sí (`15/15` variantes no equivalentes) | 🗑 Eliminado |
| M2 | Inversión u omisión de guard RBAC/Auth (`get_current_tenant` vs `require_owner`, `401`, `403 ONBOARDING_REQUIRED`, firma JWT, exposición de `unit_cost`) | `app/modules/sales/router.py`, `app/core/security.py`, `app/core/db.py`, `app/modules/sales/schemas.py`, `app/modules/sales/service.py` | `tests/integration/test_sales_api.py`, `tests/integration/test_auth_onboarding.py` | Parcial en `test_sales_api.py` (`5/6`); `6/6` con `test_auth_onboarding.py` (`M2d_jwt_sig` no cubierto en `test_sales_api.py`) | 🗑 Eliminado (con observación en `M2d_jwt_sig`) |
| M3 | Omisión de contexto RLS (`get_tenant_db`, `app.current_business_id`, `SET LOCAL ROLE app_api`, `app.current_user_id`), IDOR (`business_id` en body) y filtros `sale_id` en reintento idempotente | `app/modules/sales/router.py`, `app/core/db.py`, `app/modules/sales/schemas.py`, `app/modules/sales/service.py`, `app/modules/sales/repository.py` | `tests/integration/test_sales_api.py`, `tests/integration/test_auth_onboarding.py` | **No** (`4/7` en `test_sales_api.py`; `5/7` con `auth`; **2 sobrevivientes reales**: `M3f_items_sale_id`, `M3g_payments_sale_id`) | 🧟 Sobreviviente |
| M4 | Mutación de operadores/reglas de dominio (redondeo `ROUND_HALF_UP` vs `ROUND_HALF_EVEN`/`ROUND_DOWN`, signo de descuento de stock, saldo negativo, acumulación de líneas, cuadratura de pagos, congelamiento `unit_price`/`unit_cost`, idempotencia temprana/concurrente, `subtotal <= 0` por línea, `FOR UPDATE`, `ORDER BY id`, orden determinista `(created_at, id)`) | `app/modules/sales/service.py`, `app/modules/sales/repository.py`, `app/modules/catalog/repository.py` | `tests/integration/test_sales_api.py` | **No** (`14/20`; **6 sobrevivientes reales**: `M4b_round_even`, `M4m_subtotal_zero`, `M4o_for_update`, `M4p_order_by_id`, `M4s_items_sort`, `M4t_payments_sort`) | 🧟 Sobreviviente |
| M5 | Enmascaramiento de excepciones de dominio, status codes (`200`/`201`/`404`/`422` → `400`/`500`), código de error, formato `ErrorResponse` y `details` estructurados | `app/modules/sales/router.py`, `app/modules/sales/repository.py` | `tests/integration/test_sales_api.py` | **No** (`11/12`; **1 sobreviviente real**: `M5m_error_details`) | 🧟 Sobreviviente |

---

### Detalle de Variantes Evaluadas en Entorno Aislado (Ejecución Fail-Fast `-x`)

| Variante | Descripción de la Mutación | Archivo Mutado | Resultado / Primer Test que Atrapó el Fallo (`-x`) | Estado |
|---|---|---|---|---|
| `M1a1` | Permitir `float` en `parse_strict_decimal` (`Decimal(str(value))`) | `app/core/schemas.py` | `test_sales_api.py::test_reject_float_bool_nonfinite_scale_nonpositive_and_overflow[1.5-10.00]` | 🗑 Eliminado |
| `M1a2` | Eliminar `@field_validator("quantity", mode="before")` en `SaleItemCreate` | `app/modules/sales/schemas.py` | `test_sales_api.py::test_reject_float_bool_nonfinite_scale_nonpositive_and_overflow[1.5-10.00]` | 🗑 Eliminado |
| `M1a3` | Eliminar `@field_validator("amount", mode="before")` en `SalePaymentCreate` | `app/modules/sales/schemas.py` | `test_sales_api.py::test_reject_float_bool_nonfinite_scale_nonpositive_and_overflow[1.00-10.5]` | 🗑 Eliminado |
| `M1b` | Desactivar rechazo de `>2` decimales en `parse_strict_decimal` | `app/core/schemas.py` | `test_sales_api.py::test_reject_float_bool_nonfinite_scale_nonpositive_and_overflow[1.234-10.00]` | 🗑 Eliminado |
| `M1c` | Permitir `bool` en `parse_strict_decimal` | `app/core/schemas.py` | `test_sales_api.py::test_reject_float_bool_nonfinite_scale_nonpositive_and_overflow[True-10.00]` | 🗑 Eliminado |
| `M1d` | Desactivar validación `parsed.is_finite()` (`NaN` / `Infinity`) | `app/core/schemas.py` | `test_sales_api.py::test_reject_float_bool_nonfinite_scale_nonpositive_and_overflow[NaN-10.00]` | 🗑 Eliminado |
| `M1e` | Relajar `SaleItemCreate.quantity` `gt=Decimal("0")` a `ge=Decimal("0")` | `app/modules/sales/schemas.py` | `test_sales_api.py::test_reject_float_bool_nonfinite_scale_nonpositive_and_overflow[0.00-10.00]` | 🗑 Eliminado |
| `M1f` | Relajar `SalePaymentCreate.amount` `gt=Decimal("0")` a `ge=Decimal("0")` | `app/modules/sales/schemas.py` | `test_sales_api.py::test_reject_float_bool_nonfinite_scale_nonpositive_and_overflow[1.00-0.00]` | 🗑 Eliminado |
| `M1g_only_le` | Omitir `le=MAX_NUMERIC_12_2` en `sales/schemas.py` y cota en `core/schemas.py` (manteniendo `max_digits=12`) | `app/core/schemas.py`, `app/modules/sales/schemas.py` | `test_sales_api.py::test_openapi_documents_sales_routes_and_schemas` *(drift OpenAPI)* | 🗑 Eliminado |
| `M1g_full` | Omitir `le=MAX_NUMERIC_12_2`, `max_digits=12`, `decimal_places=2` y cota en `parse_strict_decimal` | `app/core/schemas.py`, `app/modules/sales/schemas.py` | `test_sales_api.py::test_reject_float_bool_nonfinite_scale_nonpositive_and_overflow[10000000000.00-10.00]` | 🗑 Eliminado |
| `M1h_items_min` | Omitir `min_length=1` en `SaleCreate.items` | `app/modules/sales/schemas.py` | `test_sales_api.py::test_openapi_documents_sales_routes_and_schemas` *(nota: `items=[]` pasó validación hasta `SaleTotalInvalidError` `422`)* | 🗑 Eliminado |
| `M1h_payments_min` | Omitir `min_length=1` en `SaleCreate.payments` | `app/modules/sales/schemas.py` | `test_sales_api.py::test_reject_empty_lists_invalid_method_invalid_uuid_or_nul_bytes[payload1]` | 🗑 Eliminado |
| `M1i_items_max` | Omitir `max_length=500` en `SaleCreate.items` | `app/modules/sales/schemas.py` | `test_sales_api.py::test_openapi_documents_sales_routes_and_schemas` *(solo por `maxItems` OpenAPI; sin test HTTP `422` de 501 ítems)* | 🗑 Eliminado |
| `M1i_payments_max` | Omitir `max_length=20` en `SaleCreate.payments` | `app/modules/sales/schemas.py` | `test_sales_api.py::test_openapi_documents_sales_routes_and_schemas` *(solo por `maxItems` OpenAPI; sin test HTTP `422` de 21 pagos)* | 🗑 Eliminado |
| `M1j_method` | Relajar `PaymentMethod = Literal["cash", "card", "transfer"]` a `str` | `app/modules/sales/schemas.py` | `test_sales_api.py::test_reject_empty_lists_invalid_method_invalid_uuid_or_nul_bytes[payload2]` | 🗑 Eliminado |
| `M2a_role` | Cambiar `Depends(get_current_tenant)` por `Depends(require_owner)` en `POST /sales` | `app/modules/sales/router.py` | `test_sales_api.py::test_owner_and_cashier_authorized_without_exposing_unit_cost[cashier]` | 🗑 Eliminado |
| `M2b_unauth` | Omitir rechazo `401 UNAUTHENTICATED` cuando falta cookie en `get_current_user` | `app/core/security.py` | `test_sales_api.py::test_unauthenticated_and_onboarding_pending_rejected` | 🗑 Eliminado |
| `M2c_onb` | Desactivar guard `403 ONBOARDING_REQUIRED` en `get_current_tenant` y `get_tenant_db` | `app/core/security.py`, `app/core/db.py` | `test_sales_api.py::test_unauthenticated_and_onboarding_pending_rejected` | 🗑 Eliminado |
| `M2d_jwt_sig` | Desactivar verificación de firma JWT (`verify_signature: False`) en `decode_access_token` | `app/core/security.py` | **Sobrevivió** en `test_sales_api.py` (`41 passed`); **Eliminado** en `test_auth_onboarding.py::test_onboarding_unauthenticated_returns_401` | 🗑 Eliminado (solo vía `auth`) |
| `M2e_unit_cost` | Exponer `unit_cost` en `SaleItemResponse` | `app/modules/sales/schemas.py`, `app/modules/sales/service.py` | `test_sales_api.py::test_create_sale_single_payment_and_frozen_snapshots` | 🗑 Eliminado |
| `M2f_router_no_auth` | Reemplazar `get_current_tenant` y `get_tenant_db` por dependencia anónima + `get_db` en `sales/router.py` | `app/modules/sales/router.py` | `test_sales_api.py::test_create_sale_single_payment_and_frozen_snapshots` | 🗑 Eliminado |
| `M3a_get_db` | Reemplazar `Depends(get_tenant_db)` por `Depends(get_db)` en `get_sales_service` | `app/modules/sales/router.py` | `test_sales_api.py::test_create_sale_single_payment_and_frozen_snapshots` | 🗑 Eliminado |
| `M3b_rls_biz` | Omitir `set_rls_business_context` en `get_tenant_db` | `app/core/db.py` | `test_sales_api.py::test_create_sale_single_payment_and_frozen_snapshots` | 🗑 Eliminado |
| `M3c_rls_role` | Omitir `SET LOCAL ROLE app_api` en `set_rls_user_context` | `app/core/db.py` | `test_sales_api.py::test_create_sale_single_payment_and_frozen_snapshots` | 🗑 Eliminado |
| `M3d_idor` | Aceptar `business_id` en `SaleCreate` y priorizar `payload.business_id` en `SalesService.create_sale` | `app/modules/sales/schemas.py`, `app/modules/sales/service.py` | `test_sales_api.py::test_cross_tenant_or_missing_product_rejected_404_and_body_business_id_ignored` | 🗑 Eliminado |
| `M3e_user_ctx` | Omitir `set_config('app.current_user_id', ...)` en `set_rls_user_context` | `app/core/db.py` | **Sobrevivió** en `test_sales_api.py` (`41 passed`); **Eliminado** en `test_auth_onboarding.py::test_login_success_with_existing_business` | 🗑 Eliminado (solo vía `auth`) |
| `M3f_items_sale_id` | Omitir filtro `SaleItem.sale_id == sale.id` en `SalesRepository.get_sale_by_client_id` | `app/modules/sales/repository.py` | **0 fallos (`41 passed` en `test_sales_api.py`)** | 🧟 **Sobreviviente** |
| `M3g_payments_sale_id` | Omitir filtro `Payment.sale_id == sale.id` en `SalesRepository.get_sale_by_client_id` | `app/modules/sales/repository.py` | **0 fallos (`41 passed` en `test_sales_api.py`)** | 🧟 **Sobreviviente** |
| `M4a_round_down` | Cambiar `ROUND_HALF_UP` a `ROUND_DOWN` en `_calculate_subtotal` | `app/modules/sales/service.py` | `test_sales_api.py::test_fractional_quantity_rounding_and_duplicate_product_lines` | 🗑 Eliminado |
| `M4b_round_even` | Cambiar `ROUND_HALF_UP` a `ROUND_HALF_EVEN` (default Python) en `_calculate_subtotal` | `app/modules/sales/service.py` | **0 fallos (`41 passed` en `test_sales_api.py`)** | 🧟 **Sobreviviente** |
| `M4c_stock_sign` | Sumar stock (`Product.stock + qty`) en lugar de restar en `deduct_stock_batch` | `app/modules/catalog/repository.py` | `test_sales_api.py::test_create_sale_single_payment_and_frozen_snapshots` | 🗑 Eliminado |
| `M4d_stock_neg_reject` | Rechazar venta cuando `product.stock < qty` (impedir saldo negativo) | `app/modules/sales/service.py` | `test_sales_api.py::test_counter_sale_succeeds_when_stock_becomes_negative` | 🗑 Eliminado |
| `M4e_dup_overwrite` | Sobrescribir `stock_deductions[pid] = item.quantity` en lugar de acumular líneas repetidas | `app/modules/sales/service.py` | `test_sales_api.py::test_fractional_quantity_rounding_and_duplicate_product_lines` | 🗑 Eliminado |
| `M4f_pay_lt` | Cambiar `payments_total != total_amount` a `<` (permitir sobrepago) | `app/modules/sales/service.py` | `test_sales_api.py::test_reject_payment_total_mismatch[3000.01]` | 🗑 Eliminado |
| `M4g_pay_gt` | Cambiar `payments_total != total_amount` a `>` (permitir subpago) | `app/modules/sales/service.py` | `test_sales_api.py::test_reject_payment_total_mismatch[2999.99]` | 🗑 Eliminado |
| `M4h_unit_cost_zero` | Fijar `unit_cost = Decimal("0.00")` en lugar de `product.cost_price` | `app/modules/sales/service.py` | `test_sales_api.py::test_create_sale_single_payment_and_frozen_snapshots` | 🗑 Eliminado |
| `M4i_unit_price_cost` | Usar `product.cost_price` en lugar de `product.sale_price` como `unit_price` | `app/modules/sales/service.py` | `test_sales_api.py::test_create_sale_single_payment_and_frozen_snapshots` | 🗑 Eliminado |
| `M4j_no_early_idemp` | Omitir lectura temprana `get_sale_by_client_id` antes de bloquear productos | `app/modules/sales/service.py` | `test_sales_api.py::test_sequential_idempotent_retry_returns_200_even_after_catalog_change` | 🗑 Eliminado |
| `M4k_no_on_conflict` | Omitir `.on_conflict_do_nothing(index_elements=["business_id", "client_id"])` | `app/modules/sales/repository.py` | `test_sales_api.py::test_concurrent_idempotent_retries_deduct_stock_once` | 🗑 Eliminado |
| `M4l_deduct_before_conflict` | Ejecutar `deduct_stock_batch` antes de verificar conflicto `inserted_sale is not None` | `app/modules/sales/service.py` | `test_sales_api.py::test_concurrent_idempotent_retries_deduct_stock_once` | 🗑 Eliminado |
| `M4m_subtotal_zero` | Omitir chequeo por línea `subtotal <= Decimal("0.00")` manteniendo solo `total_amount <= 0` | `app/modules/sales/service.py` | **0 fallos (`41 passed` en `test_sales_api.py`)** | 🧟 **Sobreviviente** |
| `M4n_total_overflow` | Omitir chequeos `total_amount > MAX_NUMERIC_12_2` en `SalesService.create_sale` | `app/modules/sales/service.py` | `test_sales_api.py::test_reject_sale_total_rounding_to_zero_or_overflow` | 🗑 Eliminado |
| `M4o_for_update` | Omitir `.with_for_update()` en `CatalogRepository.lock_products_for_sale` | `app/modules/catalog/repository.py` | **0 fallos (`41 passed` en `test_sales_api.py`)** | 🧟 **Sobreviviente** |
| `M4p_order_by_id` | Omitir `.order_by(Product.id.asc())` en `CatalogRepository.lock_products_for_sale` | `app/modules/catalog/repository.py` | **0 fallos (`41 passed` en `test_sales_api.py`)** | 🧟 **Sobreviviente** |
| `M4q_inactive` | Desactivar validación `if inactive_ids: raise SaleProductInactiveError(...)` | `app/modules/sales/service.py` | `test_sales_api.py::test_reject_inactive_product_for_new_sale` | 🗑 Eliminado |
| `M4r_idemp_names` | Omitir `get_product_names_by_ids` en el camino idempotente temprano (`product_names = {}`) | `app/modules/sales/service.py` | `test_sales_api.py::test_sequential_idempotent_retry_returns_200_even_after_catalog_change` | 🗑 Eliminado |
| `M4s_items_sort` | Omitir ordenamiento determinista `(created_at, id)` en `insert_sale_items` y `get_sale_by_client_id` | `app/modules/sales/repository.py` | **0 fallos (`41 passed` en `test_sales_api.py`)** | 🧟 **Sobreviviente** |
| `M4t_payments_sort` | Omitir ordenamiento determinista `(created_at, id)` en `insert_payments` y `get_sale_by_client_id` | `app/modules/sales/repository.py` | **0 fallos (`41 passed` en `test_sales_api.py`)** | 🧟 **Sobreviviente** |
| `M5a_notfound_500` | Devolver `500` en lugar de `404` ante `SaleProductNotFoundError` | `app/modules/sales/router.py` | `test_sales_api.py::test_cross_tenant_or_missing_product_rejected_404_and_body_business_id_ignored` | 🗑 Eliminado |
| `M5b_notfound_422` | Devolver `422` en lugar de `404` ante `SaleProductNotFoundError` | `app/modules/sales/router.py` | `test_sales_api.py::test_cross_tenant_or_missing_product_rejected_404_and_body_business_id_ignored` | 🗑 Eliminado |
| `M5c_notfound_code` | Alterar `"code": "PRODUCT_NOT_FOUND"` a `"NOT_FOUND"` | `app/modules/sales/router.py` | `test_sales_api.py::test_cross_tenant_or_missing_product_rejected_404_and_body_business_id_ignored` | 🗑 Eliminado |
| `M5d_inactive_500` | Devolver `500` en lugar de `422` ante `SaleProductInactiveError` | `app/modules/sales/router.py` | `test_sales_api.py::test_reject_inactive_product_for_new_sale` | 🗑 Eliminado |
| `M5e_inactive_code` | Alterar `"code": "PRODUCT_INACTIVE"` a `"VALIDATION_ERROR"` | `app/modules/sales/router.py` | `test_sales_api.py::test_reject_inactive_product_for_new_sale` | 🗑 Eliminado |
| `M5f_mismatch_400` | Devolver `400` en lugar de `422` ante `SalePaymentMismatchError` | `app/modules/sales/router.py` | `test_sales_api.py::test_reject_payment_total_mismatch[2999.99]` | 🗑 Eliminado |
| `M5g_mismatch_code` | Alterar `"code": "PAYMENT_TOTAL_MISMATCH"` a `"VALIDATION_ERROR"` | `app/modules/sales/router.py` | `test_sales_api.py::test_reject_payment_total_mismatch[2999.99]` | 🗑 Eliminado |
| `M5h_invalid_500` | Devolver `500` en lugar de `422` ante `SaleTotalInvalidError` | `app/modules/sales/router.py` | `test_sales_api.py::test_reject_sale_total_rounding_to_zero_or_overflow` | 🗑 Eliminado |
| `M5i_always_201` | Devolver siempre `201 Created` (incluso en reintento idempotente) | `app/modules/sales/router.py` | `test_sales_api.py::test_sequential_idempotent_retry_returns_200_even_after_catalog_change` | 🗑 Eliminado |
| `M5j_always_200` | Devolver siempre `200 OK` (incluso en creación nueva) | `app/modules/sales/router.py` | `test_sales_api.py::test_create_sale_single_payment_and_frozen_snapshots` | 🗑 Eliminado |
| `M5k_detail_wrap` | Devolver `detail` string plano en lugar de estructura `ErrorResponse` en `404` | `app/modules/sales/router.py` | `test_sales_api.py::test_cross_tenant_or_missing_product_rejected_404_and_body_business_id_ignored` | 🗑 Eliminado |
| `M5m_error_details` | Omitir `details` (`details=None`) en `PRODUCT_NOT_FOUND`, `PRODUCT_INACTIVE` y `PAYMENT_TOTAL_MISMATCH` | `app/modules/sales/router.py` | **0 fallos (`41 passed` en `test_sales_api.py`)** | 🧟 **Sobreviviente** |

### Mutantes Equivalentes Verificados (Excluidos del Denominador)

| Variante | Descripción | Por qué es Equivalente en Flujo HTTP |
|---|---|---|
| `M1k_nul` | Omitir `reject_nul_byte` en `validate_product_id_nul`, `validate_payment_method_nul` y `validate_client_id_nul` (`app/modules/sales/schemas.py`) | `uuid.UUID` y `PaymentMethod = Literal["cash", "card", "transfer"]` ya rechazan strings con `\x00` emitiendo igualmente HTTP `422 VALIDATION_ERROR`. |
| `M3h_sale_biz_filter` | Omitir `Sale.business_id == business_id` en `SalesRepository.get_sale_by_client_id` (`app/modules/sales/repository.py:41`) | Bajo `get_tenant_db` (`app_api`), la política RLS `sales_select_isolation` fuerza `business_id = NULLIF(current_setting('app.current_business_id', true), '')::uuid`, haciendo redundante el predicado explícito mientras RLS esté activo. |
| `M5l_savepoint` | Omitir `async with self._session.begin_nested():` en `SalesRepository.transaction` (`app/modules/sales/repository.py:25`) | En `POST /api/v1/sales`, `get_tenant_db` ya abre `async with session.begin():` y `SalesService.create_sale` no captura ni recupera excepciones alrededor de `self._repository.transaction()`; toda excepción revierte la transacción externa completa. |
| `M5n_no_txn_in_repo` | Reemplazar `SalesRepository.transaction` por `yield` directo (`app/modules/sales/repository.py:22-29`) | Equivalente bajo `get_tenant_db` por la misma razón que `M5l_savepoint` (el `else: session.begin()` solo aplicaría si un caller invocara `SalesService` sin transacción previa). |

---

## 3. Brechas de Falsabilidad y Acción Requerida

Se detectaron **9 mutantes no equivalentes sobrevivientes**, **1 test baseline flaky (no determinista)** y **3 observaciones de cobertura local/funcional** que requieren reforzar `backend/tests/integration/test_sales_api.py` (y opcionalmente `backend/tests/unit/test_sales_schemas.py`):

1. **🐛 Defecto crítico en test existente (Flaky por UUID aleatorio en `test_sales_api.py:372-376`):**
   - `test_create_sale_combined_payments_exact_decimal_sum` inserta 3 pagos (`cash`, `card`, `transfer`) en un único `INSERT` donde `created_at` comparte `now()` transaccional y `id` usa `gen_random_uuid()`. `SalesRepository.insert_payments` ordena por `(row.created_at, row.id)` —lo cual produce una permutación aleatoria— pero el test aserta igualdad de lista fija `[("cash", "0.10"), ("card", "0.10"), ("transfer", "0.10")]`. En `5/5` corridas aisladas consecutivas el test falló (`At index 0 diff: ('card', '0.10') != ('cash', '0.10')` / `('transfer', '0.10')`).
   - **Acción:** En `test_create_sale_combined_payments_exact_decimal_sum`, comparar el conjunto o lista ordenada (`sorted(...)`) por `(payment_method, amount)`, sin asumir orden de inserción frente a UUIDs aleatorios.

2. **🧟 Brechas 1 y 2 (`M3f_items_sale_id`, `M3g_payments_sale_id` — Fuga de líneas/pagos de otras ventas en reintento idempotente):**
   - Omitir `SaleItem.sale_id == sale.id` (`sales/repository.py:52`) o `Payment.sale_id == sale.id` (`sales/repository.py:62`) pasa todos los tests porque ningún test de idempotencia crea previamente otra venta en el mismo `business_id`.
   - **Acción:** En `test_sequential_idempotent_retry_returns_200_even_after_catalog_change` (o nuevo test), registrar primero una **venta previa distinta** (`client_id_prev`) con su propio producto y pago dentro del mismo `business_id`, luego registrar y reintentar la venta objetivo (`client_id_target`) y asertar `len(retry_resp.json()["items"])`, `len(retry_resp.json()["payments"])` y exactitud de sus IDs.

3. **🧟 Brecha 3 (`M4b_round_even` — `ROUND_HALF_UP` vs `ROUND_HALF_EVEN`):**
   - `test_fractional_quantity_rounding_and_duplicate_product_lines` solo prueba `1.50 * 100.33 = 150.495` (centésimo impar `9`), caso donde `ROUND_HALF_EVEN` coincide con `ROUND_HALF_UP` (`150.50`).
   - **Acción:** Agregar un caso de empate con centésimo par, p. ej. `sale_price = "100.35"` y `quantity = "1.50"` (`150.525` → debe ser `"150.53"` bajo `ROUND_HALF_UP`, no `"150.52"`), o `sale_price = "0.05"` y `quantity = "0.50"` (`0.025` → `"0.03"`).

4. **🧟 Brecha 4 (`M4m_subtotal_zero` — Línea individual con subtotal `0.00` en venta multi-ítem):**
   - `test_reject_sale_total_rounding_to_zero_or_overflow` prueba únicamente una venta de 1 línea (`0.01 * 0.01 = 0.00`), atrapada por `total_amount <= 0` (`service.py:165`) aunque se elimine el chequeo por línea (`service.py:145`).
   - **Acción:** Agregar un caso multi-ítem combinando un producto válido (`10.00`) + un producto centavo (`0.01 * 0.01 = 0.00`) con pago `10.00` y asertar rechazo `422 VALIDATION_ERROR` sin persistir filas.

5. **🧟 Brechas 5 y 6 (`M4o_for_update`, `M4p_order_by_id` — Bloqueo determinista `ORDER BY id ASC FOR UPDATE`):**
   - Ningún test inspecciona el SQL de `CatalogRepository.lock_products_for_sale` ni verifica `FOR UPDATE` / `ORDER BY products.id ASC`.
   - **Acción:** En `_capture_sql_statements()`, verificar sobre el `SELECT ... FROM products` de `POST /api/v1/sales` que contenga `order by products.id asc` y `for update` (y opcionalmente añadir prueba con múltiples productos enviados en orden descendente de UUID comprobando orden ascendente en parámetros/cláusula).

6. **🧟 Brechas 7 y 8 (`M4s_items_sort`, `M4t_payments_sort` — Determinismo `(created_at, id)` entre `201` y `200`):**
   - Ningún test de reintento idempotente usa una venta con `>= 2` ítems y `>= 2` pagos para comprobar que el orden de `items` y `payments` devuelto en `200 OK` coincide exactamente con el de `201 Created` (`retry_resp.json() == first_resp.json()`).
   - **Acción:** Ampliar la prueba de idempotencia secuencial para incluir una venta con `>= 2` líneas y `>= 2` métodos de pago, verificando que los IDs en `items` y `payments` vengan ordenados por `(created_at, id)` y sean idénticos entre `201` y `200`.

7. **🧟 Brecha 9 (`M5m_error_details` — Contenido estructurado de `details` en `404`/`422`):**
   - `_assert_uniform_error_response` valida `set(body.keys()) == {"code", "message", "details"}`, pero nunca verifica `details["missing_product_ids"]` (`404`), `details["inactive_product_ids"]` (`422 PRODUCT_INACTIVE`) ni `details["expected_total"]` / `details["payments_total"]` (`422 PAYMENT_TOTAL_MISMATCH`) definidos en `design.md`.
   - **Acción:** Asertar explícitamente esas claves y valores en los tests de `404` y `422` correspondientes.

8. **ℹ️ Observaciones adicionales (Cobertura local en `test_sales_api.py`):**
   - **`M2d_jwt_sig`:** `test_sales_api.py` no prueba un JWT con firma inválida o expirado sobre `POST /api/v1/sales` (actualmente cubierto solo vía `test_auth_onboarding.py`). Conviene agregar un caso en `test_unauthenticated_and_onboarding_pending_rejected` enviando cookie con firma errónea y token expirado → `401 UNAUTHENTICATED`.
   - **`M1i_items_max`, `M1i_payments_max`, `M1h_items_min`:** Aunque fueron atrapados por `test_openapi_documents_sales_routes_and_schemas` (`maxItems` / `minItems`), conviene verificar en assertions que `items=[]` no llegue a `get_tenant_db` ni a consultar `products` (actualmente solo se asertó `not any("insert into sales" ...)`), y probar explícitamente límites `501` ítems / `21` pagos → `422 VALIDATION_ERROR`.

### Siguiente Paso Recomendado (`backend-sdd`)
- Re-despachar a `backend-test-writer-agent` (con este `mutation-report.md`) para corregir el test flaky (`test_sales_api.py:372`) y reforzar las aserciones de `backend/tests/integration/test_sales_api.py` cubriendo las brechas `M3f`, `M3g`, `M4b`, `M4m`, `M4o`, `M4p`, `M4s`, `M4t`, `M5m` y `M2d`, re-congelar la huella SHA-256 en `.sdd-state.json`, re-ejecutar Gate 4 y repetir el Paso 5 (`backend-mutation-tester`) hasta obtener `[TESTS BLINDADOS]`.
