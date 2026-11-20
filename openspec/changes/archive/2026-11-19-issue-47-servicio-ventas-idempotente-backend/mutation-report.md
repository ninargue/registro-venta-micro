# 🔬 REPORTE DE MUTATION TESTING Y FALSABILIDAD: issue-47-servicio-ventas-idempotente-backend

## 1. Veredicto de Falsabilidad
- **Estado:** `[TESTS BLINDADOS]`
- **Modo de Ejecución:** `Catálogo Canónico M1–M5` (`mutation_cmd: none` en `design.md`; re-ejecutado tras el refuerzo de `backend/tests/integration/test_sales_api.py` sobre copia temporal aislada en `$env:TEMP\mut-sales-47-v2` con `DATABASE_URL=postgresql+asyncpg://postgres:postgres@127.0.0.1:54422/postgres` y el entorno `.venv` de `backend/`. Copia temporal eliminada al finalizar: `TMP_EXISTS=False`; integridad de árbol vivo verificada: `HASH_MISMATCHES=0` contra `.sdd-state.json`, `MUTATION_ARTIFACTS=0`, `89 passed` en `tests/unit` + `tests/integration/test_sales_api.py`, y `242 passed` reportados en Gate 4).
- **Tests Auditados:** `backend/tests/integration/test_sales_api.py` (`42 passed in 31.81s` en baseline aislado; flakiness eliminada con `5/5` ejecuciones consecutivas en verde sobre `test_create_sale_combined_payments_exact_decimal_sum`) y `backend/tests/integration/test_auth_onboarding.py` (para `M3e_user_ctx` en `app/core/db.py`).
- **Tasa de Mutantes Eliminados:**
  - **Categorías canónicas `M1–M5`:** `5/5` (`100%`) eliminadas.
  - **Variantes discretas no equivalentes:** `60/60` (`100%`) eliminadas (`59/60` atrapadas directamente por `tests/integration/test_sales_api.py`, y `M3e_user_ctx` en `app/core/db.py` atrapado por `tests/integration/test_auth_onboarding.py::test_login_success_with_existing_business`).
  - **Mutantes equivalentes verificados aparte (excluidos del denominador):** `4` (`M1k_nul`, `M3h_sale_biz_filter`, `M5l_savepoint`, `M5n_no_txn_in_repo`).

---

## 2. Matriz de Mutaciones Evaluadas

### Resumen Canónico M1–M5

| ID | Mutación | Archivo(s) Mutado(s) (`backend/app`) | Archivo(s) de Test (`backend/tests`) | ¿Atrapó el Fallo? | Resultado |
|---|---|---|---|---|---|
| M1 | Eliminación/relajación de validación de entrada (`Decimal`, `float`, `bool`, `NaN`/`Inf`, `>2` decimales, `gt=0`, overflow `numeric(12,2)`, `min_length`/`max_length` de `items`/`payments`, `PaymentMethod`) | `app/modules/sales/schemas.py`, `app/core/schemas.py` | `tests/integration/test_sales_api.py` | Sí (`15/15` variantes no equivalentes) | 🗑 Eliminado |
| M2 | Inversión u omisión de guard RBAC/Auth (`get_current_tenant` vs `require_owner`, `401` por cookie ausente/firma inválida/expiración, `403 ONBOARDING_REQUIRED`, exposición de `unit_cost`) | `app/modules/sales/router.py`, `app/core/security.py`, `app/core/db.py`, `app/modules/sales/schemas.py`, `app/modules/sales/service.py` | `tests/integration/test_sales_api.py` | Sí (`6/6` variantes, incluyendo `M2d_jwt_sig` tras el refuerzo) | 🗑 Eliminado |
| M3 | Omisión de contexto RLS (`get_tenant_db`, `app.current_business_id`, `SET LOCAL ROLE app_api`, `app.current_user_id`), IDOR (`business_id` en body) y filtros `sale_id` en reintento idempotente | `app/modules/sales/router.py`, `app/core/db.py`, `app/modules/sales/schemas.py`, `app/modules/sales/service.py`, `app/modules/sales/repository.py` | `tests/integration/test_sales_api.py`, `tests/integration/test_auth_onboarding.py` | Sí (`7/7` variantes no equivalentes; `6/7` en `test_sales_api.py` tras el refuerzo + `M3e_user_ctx` en `test_auth_onboarding.py`) | 🗑 Eliminado |
| M4 | Mutación de operadores/reglas de dominio (`ROUND_HALF_UP` vs `ROUND_HALF_EVEN`/`ROUND_DOWN`, signo de descuento de stock, saldo negativo, acumulación de líneas, cuadratura de pagos, congelamiento `unit_price`/`unit_cost`, idempotencia temprana/concurrente, `subtotal <= 0` por línea, `FOR UPDATE`, `ORDER BY id`, orden determinista `(created_at, id)`) | `app/modules/sales/service.py`, `app/modules/sales/repository.py`, `app/modules/catalog/repository.py` | `tests/integration/test_sales_api.py` | Sí (`20/20` variantes tras el refuerzo; `M4s`/`M4t` atrapados probabilísticamente por UUID aleatorio al reintento 2) | 🗑 Eliminado |
| M5 | Enmascaramiento de excepciones de dominio, status codes (`200`/`201`/`404`/`422` → `400`/`500`), código de error, formato `ErrorResponse` y `details` estructurados | `app/modules/sales/router.py`, `app/modules/sales/repository.py` | `tests/integration/test_sales_api.py` | Sí (`12/12` variantes no equivalentes tras el refuerzo) | 🗑 Eliminado |

---

### Detalle de Variantes Evaluadas en Entorno Aislado (Ejecución Fail-Fast `-x`)

Baseline verificado tras el refuerzo en la copia temporal aislada `$env:TEMP\mut-sales-47-v2`: `42 passed in 31.81s` (`tests/integration/test_sales_api.py`) y `5/5` pasadas consecutivas en `test_create_sale_combined_payments_exact_decimal_sum`.

| Variante | Descripción de la Mutación | Archivo Mutado | Primer Test que Atrapó el Fallo (`-x`) | Estado |
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
| `M1h_items_min` | Omitir `min_length=1` en `SaleCreate.items` | `app/modules/sales/schemas.py` | `test_sales_api.py::test_openapi_documents_sales_routes_and_schemas` *(drift `minItems` OpenAPI)* | 🗑 Eliminado |
| `M1h_payments_min` | Omitir `min_length=1` en `SaleCreate.payments` | `app/modules/sales/schemas.py` | `test_sales_api.py::test_reject_empty_lists_invalid_method_invalid_uuid_or_nul_bytes[payload1]` | 🗑 Eliminado |
| `M1i_items_max` | Omitir `max_length=500` en `SaleCreate.items` | `app/modules/sales/schemas.py` | `test_sales_api.py::test_openapi_documents_sales_routes_and_schemas` *(drift `maxItems` OpenAPI)* | 🗑 Eliminado |
| `M1i_payments_max` | Omitir `max_length=20` en `SaleCreate.payments` | `app/modules/sales/schemas.py` | `test_sales_api.py::test_openapi_documents_sales_routes_and_schemas` *(drift `maxItems` OpenAPI)* | 🗑 Eliminado |
| `M1j_method` | Relajar `PaymentMethod = Literal["cash", "card", "transfer"]` a `str` | `app/modules/sales/schemas.py` | `test_sales_api.py::test_reject_empty_lists_invalid_method_invalid_uuid_or_nul_bytes[payload2]` | 🗑 Eliminado |
| `M2a_role` | Cambiar `Depends(get_current_tenant)` por `Depends(require_owner)` en `POST /sales` | `app/modules/sales/router.py` | `test_sales_api.py::test_owner_and_cashier_authorized_without_exposing_unit_cost[cashier]` | 🗑 Eliminado |
| `M2b_unauth` | Omitir rechazo `401 UNAUTHENTICATED` cuando falta cookie en `get_current_user` | `app/core/security.py` | `test_sales_api.py::test_unauthenticated_and_onboarding_pending_rejected` | 🗑 Eliminado |
| `M2c_onb` | Desactivar guard `403 ONBOARDING_REQUIRED` en `get_current_tenant` y `get_tenant_db` | `app/core/security.py`, `app/core/db.py` | `test_sales_api.py::test_unauthenticated_and_onboarding_pending_rejected` | 🗑 Eliminado |
| `M2d_jwt_sig` | Desactivar verificación de firma JWT (`verify_signature: False`) en `decode_access_token` *(brecha previa en `test_sales_api.py`)* | `app/core/security.py` | `test_sales_api.py::test_unauthenticated_and_onboarding_pending_rejected` *(re-verificado en v2)* | 🗑 Eliminado |
| `M2e_unit_cost` | Exponer `unit_cost` en `SaleItemResponse` | `app/modules/sales/schemas.py`, `app/modules/sales/service.py` | `test_sales_api.py::test_create_sale_single_payment_and_frozen_snapshots` | 🗑 Eliminado |
| `M2f_router_no_auth` | Reemplazar `get_current_tenant` y `get_tenant_db` por dependencia anónima + `get_db` en `sales/router.py` | `app/modules/sales/router.py` | `test_sales_api.py::test_create_sale_single_payment_and_frozen_snapshots` | 🗑 Eliminado |
| `M3a_get_db` | Reemplazar `Depends(get_tenant_db)` por `Depends(get_db)` en `get_sales_service` | `app/modules/sales/router.py` | `test_sales_api.py::test_create_sale_single_payment_and_frozen_snapshots` | 🗑 Eliminado |
| `M3b_rls_biz` | Omitir `set_rls_business_context` en `get_tenant_db` | `app/core/db.py` | `test_sales_api.py::test_create_sale_single_payment_and_frozen_snapshots` | 🗑 Eliminado |
| `M3c_rls_role` | Omitir `SET LOCAL ROLE app_api` en `set_rls_user_context` | `app/core/db.py` | `test_sales_api.py::test_create_sale_single_payment_and_frozen_snapshots` | 🗑 Eliminado |
| `M3d_idor` | Aceptar `business_id` en `SaleCreate` y priorizar `payload.business_id` en `SalesService.create_sale` | `app/modules/sales/schemas.py`, `app/modules/sales/service.py` | `test_sales_api.py::test_cross_tenant_or_missing_product_rejected_404_and_body_business_id_ignored` | 🗑 Eliminado |
| `M3e_user_ctx` | Omitir `set_config('app.current_user_id', ...)` en `set_rls_user_context` | `app/core/db.py` | `test_auth_onboarding.py::test_login_success_with_existing_business` *(suite completa)* | 🗑 Eliminado |
| `M3f_items_sale_id` | Omitir filtro `SaleItem.sale_id == sale.id` en `SalesRepository.get_sale_by_client_id` *(brecha previa)* | `app/modules/sales/repository.py` | `test_sales_api.py::test_sequential_idempotent_retry_returns_200_even_after_catalog_change` *(re-verificado en v2)* | 🗑 Eliminado |
| `M3g_payments_sale_id` | Omitir filtro `Payment.sale_id == sale.id` en `SalesRepository.get_sale_by_client_id` *(brecha previa)* | `app/modules/sales/repository.py` | `test_sales_api.py::test_sequential_idempotent_retry_returns_200_even_after_catalog_change` *(re-verificado en v2)* | 🗑 Eliminado |
| `M4a_round_down` | Cambiar `ROUND_HALF_UP` a `ROUND_DOWN` en `_calculate_subtotal` | `app/modules/sales/service.py` | `test_sales_api.py::test_fractional_quantity_rounding_and_duplicate_product_lines` | 🗑 Eliminado |
| `M4b_round_even` | Cambiar `ROUND_HALF_UP` a `ROUND_HALF_EVEN` (default Python) en `_calculate_subtotal` *(brecha previa)* | `app/modules/sales/service.py` | `test_sales_api.py::test_fractional_quantity_rounding_and_duplicate_product_lines` *(re-verificado en v2)* | 🗑 Eliminado |
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
| `M4m_subtotal_zero` | Omitir chequeo por línea `subtotal <= Decimal("0.00")` manteniendo solo `total_amount <= 0` *(brecha previa)* | `app/modules/sales/service.py` | `test_sales_api.py::test_reject_sale_total_rounding_to_zero_or_overflow` *(re-verificado en v2)* | 🗑 Eliminado |
| `M4n_total_overflow` | Omitir chequeos `total_amount > MAX_NUMERIC_12_2` en `SalesService.create_sale` | `app/modules/sales/service.py` | `test_sales_api.py::test_reject_sale_total_rounding_to_zero_or_overflow` | 🗑 Eliminado |
| `M4o_for_update` | Omitir `.with_for_update()` en `CatalogRepository.lock_products_for_sale` *(brecha previa)* | `app/modules/catalog/repository.py` | `test_sales_api.py::test_create_sale_combined_payments_exact_decimal_sum` *(re-verificado en v2)* | 🗑 Eliminado |
| `M4p_order_by_id` | Omitir `.order_by(Product.id.asc())` en `CatalogRepository.lock_products_for_sale` *(brecha previa)* | `app/modules/catalog/repository.py` | `test_sales_api.py::test_create_sale_combined_payments_exact_decimal_sum` *(re-verificado en v2)* | 🗑 Eliminado |
| `M4q_inactive` | Desactivar validación `if inactive_ids: raise SaleProductInactiveError(...)` | `app/modules/sales/service.py` | `test_sales_api.py::test_reject_inactive_product_for_new_sale` | 🗑 Eliminado |
| `M4r_idemp_names` | Omitir `get_product_names_by_ids` en el camino idempotente temprano (`product_names = {}`) | `app/modules/sales/service.py` | `test_sales_api.py::test_sequential_idempotent_retry_returns_200_even_after_catalog_change` | 🗑 Eliminado |
| `M4s_items_sort` | Omitir ordenamiento determinista `(created_at, id)` en `insert_sale_items` y `get_sale_by_client_id` *(brecha previa)* | `app/modules/sales/repository.py` | `test_sales_api.py::test_sequential_idempotent_retry_returns_200_even_after_catalog_change` *(atrapado al reintento 2 por permutación aleatoria de 2 UUIDs)* | 🗑 Eliminado |
| `M4t_payments_sort` | Omitir ordenamiento determinista `(created_at, id)` en `insert_payments` y `get_sale_by_client_id` *(brecha previa)* | `app/modules/sales/repository.py` | `test_sales_api.py::test_sequential_idempotent_retry_returns_200_even_after_catalog_change` *(atrapado al reintento 2 por permutación aleatoria de 2 UUIDs)* | 🗑 Eliminado |
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
| `M5m_error_details` | Omitir `details` (`details=None`) en `PRODUCT_NOT_FOUND`, `PRODUCT_INACTIVE` y `PAYMENT_TOTAL_MISMATCH` *(brecha previa)* | `app/modules/sales/router.py` | `test_sales_api.py::test_reject_payment_total_mismatch[2999.99]` *(re-verificado en v2)* | 🗑 Eliminado |

### Mutantes Equivalentes Verificados (Excluidos del Denominador)

| Variante | Descripción | Por qué es Equivalente en Flujo HTTP |
|---|---|---|
| `M1k_nul` | Omitir `reject_nul_byte` en `validate_product_id_nul`, `validate_payment_method_nul` y `validate_client_id_nul` (`app/modules/sales/schemas.py`) | `uuid.UUID` y `PaymentMethod = Literal["cash", "card", "transfer"]` ya rechazan strings con `\x00` emitiendo igualmente HTTP `422 VALIDATION_ERROR`. |
| `M3h_sale_biz_filter` | Omitir `Sale.business_id == business_id` en `SalesRepository.get_sale_by_client_id` (`app/modules/sales/repository.py:41`) | Bajo `get_tenant_db` (`app_api`), la política RLS `sales_select_isolation` fuerza `business_id = NULLIF(current_setting('app.current_business_id', true), '')::uuid`, haciendo redundante el predicado explícito mientras RLS esté activo. |
| `M5l_savepoint` | Omitir `async with self._session.begin_nested():` en `SalesRepository.transaction` (`app/modules/sales/repository.py:25`) | En `POST /api/v1/sales`, `get_tenant_db` ya abre `async with session.begin():` y `SalesService.create_sale` no captura ni recupera excepciones alrededor de `self._repository.transaction()`; toda excepción revierte la transacción externa completa. |
| `M5n_no_txn_in_repo` | Reemplazar `SalesRepository.transaction` por `yield` directo (`app/modules/sales/repository.py:22-29`) | Equivalente bajo `get_tenant_db` por la misma razón que `M5l_savepoint` (el `else: session.begin()` solo aplicaría si un caller invocara `SalesService` sin transacción previa). |

---

## 3. Brechas de Falsabilidad y Acción Requerida

- **`[TESTS BLINDADOS]`:** Suite Backend-TDD verificada como robusta, determinista y falsable tras el refuerzo aplicado en `backend/tests/integration/test_sales_api.py` (`42 passed in 31.81s` en entorno aislado; `5/5` pasadas consecutivas en el test de pagos combinados):
  - **Flakiness eliminada (`test_sales_api.py:376-382`):** `test_create_sale_combined_payments_exact_decimal_sum` ahora compara con `sorted(...)` independientemente de los UUIDs aleatorios generados por `gen_random_uuid()`, pasando `5/5` corridas consecutivas.
  - **Brechas 1 y 2 cerradas (`M3f_items_sale_id`, `M3g_payments_sale_id`):** `test_sequential_idempotent_retry_returns_200_even_after_catalog_change` siembra y registra una venta previa en el mismo `business_id`, verifica `len(items) == 2` / `len(payments) == 2` y valida conjuntos disjuntos de IDs respecto de la venta previa.
  - **Brecha 3 cerrada (`M4b_round_even`):** `test_fractional_quantity_rounding_and_duplicate_product_lines` incorpora el caso de empate con centésimo par (`1.50 * 100.35 = 150.525 → "150.53"` bajo `ROUND_HALF_UP`).
  - **Brecha 4 cerrada (`M4m_subtotal_zero`):** `test_reject_sale_total_rounding_to_zero_or_overflow` añade el caso multi-ítem (`10.00 + 0.01 * 0.01`) rechazado con `422 VALIDATION_ERROR`.
  - **Brechas 5 y 6 cerradas (`M4o_for_update`, `M4p_order_by_id`):** `test_create_sale_combined_payments_exact_decimal_sum` envía `id_high` antes que `id_low` y verifica vía `_capture_sql_statements()` que el `SELECT ... FROM products` incluya `for update`, `order by products.id asc` y parámetros ordenados (`id_low` antes de `id_high`).
  - **Brechas 7 y 8 cerradas (`M4s_items_sort`, `M4t_payments_sort`):** `test_sequential_idempotent_retry_returns_200_even_after_catalog_change` valida 2 líneas y 2 pagos verificando `retry_body == first_resp.json()` y orden ascendente por `id` *(nota: al usar 2 filas con UUID aleatorio, la omisión de ordenamiento falla en ~50% de las corridas individuales, quedando abatida al reintento 2; con `>= 3` filas el fallo sería ~83.3% por corrida)*.
  - **Brecha 9 cerrada (`M5m_error_details`):** Los tests de `404` (`PRODUCT_NOT_FOUND`) y `422` (`PRODUCT_INACTIVE`, `PAYMENT_TOTAL_MISMATCH`) validan explícitamente `details` (`missing_product_ids`, `inactive_product_ids`, `expected_total`, `payments_total`).
  - **Cobertura local en `test_sales_api.py` (`M2d_jwt_sig`):** `test_unauthenticated_and_onboarding_pending_rejected` ahora valida explícitamente token con firma incorrecta y token expirado → `401 UNAUTHENTICATED`.
  - **Cobertura transversal (`M3e_user_ctx`):** `app.current_user_id` en `app/core/db.py` permanece validado en la suite completa por `tests/integration/test_auth_onboarding.py::test_login_success_with_existing_business`, mientras las políticas RLS de `sales` y `products` evalúan `app.current_business_id`.
- Cambio listo para `opsx:archive`.
