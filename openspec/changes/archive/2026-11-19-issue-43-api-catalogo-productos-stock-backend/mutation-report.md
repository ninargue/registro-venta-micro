# 🔬 REPORTE DE MUTATION TESTING Y FALSABILIDAD: issue-43-api-catalogo-productos-stock-backend

## 1. Veredicto de Falsabilidad
- **Estado:** `[TESTS BLINDADOS]`
- **Modo de Ejecución:** `Catálogo Canónico M1–M5` (`mutation_cmd: none` en `design.md`; re-ejecutado tras refuerzo de `backend/tests/integration/test_catalog_products.py` sobre copia temporal aislada en `$env:TEMP\mut_catalog_43_v2` con `uv run --project C:\Users\Armenta\Documents\Repositories\wt-43-api-catalogo-productos-stock\backend` y `PYTHONPATH` apuntando a la copia temporal; árbol vivo intacto y copia temporal eliminada al finalizar, `TMP_EXISTS=False`)
- **Tests Auditados:** `backend/tests/integration/test_catalog_products.py` (`54 passed` en baseline aislado) y `backend/tests/integration/test_auth_onboarding.py` (para `M3e` en `app/core/db.py`; `147 passed` reportados en suite completa tras Gate 4)
- **Tasa de Mutantes Eliminados:**
  - **Categorías canónicas `M1–M5`:** `5/5` (`100%`) eliminadas.
  - **Variantes discretas no equivalentes:** `44/44` (`100%`) eliminadas (`43/44` atrapadas directamente por `tests/integration/test_catalog_products.py` y `M3e` en `app/core/db.py` atrapado por `tests/integration/test_auth_onboarding.py::test_login_success_with_existing_business`).
  - **Mutantes equivalentes verificados aparte:** `2` (`M1g` y `M4i`, cuyas contrapartes no equivalentes `M1g_full` y `M4i_nostrip` fueron eliminadas).

---

## 2. Matriz de Mutaciones Evaluadas

### Resumen Canónico M1–M5

| ID | Mutación | Archivo(s) Mutado(s) (`backend/app`) | Archivo de Test (`backend/tests`) | ¿Atrapó el Fallo? | Resultado |
|---|---|---|---|---|---|
| M1 | Eliminación/relajación de validación de entrada (`Decimal`, `float`, `bool`, `NaN`/`Inf`, >2 decimales, `stock >= 0`, `cost_price >= 0`, overflow, `\x00`, `code` vacío, cotas `limit`/`offset`/`q` en `ProductListQuery`) | `app/modules/catalog/schemas.py` | `tests/integration/test_catalog_products.py` | Sí (`14/14` variantes no equivalentes) | 🗑 Eliminado |
| M2 | Inversión u omisión de guard RBAC/auth (`require_owner`, `get_current_user`, `get_current_tenant` + `get_tenant_db`, redacción de `cost_price` para `cashier`) | `app/modules/catalog/router.py`, `app/modules/catalog/service.py`, `app/core/security.py`, `app/core/db.py` | `tests/integration/test_catalog_products.py` | Sí (`6/6` variantes) | 🗑 Eliminado |
| M3 | Omisión de propagación RLS (`get_tenant_db`, `SET LOCAL ROLE app_api`, `app.current_business_id`, `app.current_user_id`) o IDOR vía `business_id` del payload | `app/modules/catalog/router.py`, `app/core/db.py`, `app/modules/catalog/schemas.py`, `app/modules/catalog/service.py` | `tests/integration/test_catalog_products.py`, `tests/integration/test_auth_onboarding.py` | Sí (`5/5` variantes; `4/5` en `catalog` + `M3e` en `auth`) | 🗑 Eliminado |
| M4 | Mutación de operador/límite de dominio (`sale_price > 0` → `>= 0`, `include_inactive`, `order_by`, escape `%`/`_`/`\`, paginación, `count`, `strip`, `stock` negativo) | `app/modules/catalog/schemas.py`, `app/modules/catalog/repository.py` | `tests/integration/test_catalog_products.py` | Sí (`13/13` variantes no equivalentes) | 🗑 Eliminado |
| M5 | Enmascaramiento de `DuplicateProductCodeError` / `23505` (`200`/`500` o código distinto en lugar de `409 Conflict`) y omisión de savepoint `begin_nested()` | `app/modules/catalog/router.py`, `app/modules/catalog/service.py`, `app/modules/catalog/repository.py` | `tests/integration/test_catalog_products.py` | Sí (`6/6` variantes) | 🗑 Eliminado |

---

### Detalle de Variantes Evaluadas en Entorno Aislado (Ejecución Fail-Fast `-x`)

Baseline verificado en la copia temporal aislada tras el refuerzo: `54 passed, 66 warnings in 37.51s` (`tests/integration/test_catalog_products.py`).

| Variante | Descripción de la Mutación | Archivo Mutado | Primer Test que Atrapó el Fallo (`-x`) | Estado |
|---|---|---|---|---|
| `M1a1` | Permitir `float` en `_parse_strict_decimal` (`Decimal(str(value))`) | `app/modules/catalog/schemas.py` | `test_catalog_products.py::test_reject_float_bool_nonfinite_and_excessive_decimal_places[payload0]` (`1 failed`) | 🗑 Eliminado |
| `M1a2` | Eliminar `@field_validator("sale_price", "cost_price", "stock", mode="before")` en `ProductCreate` | `app/modules/catalog/schemas.py` | `test_catalog_products.py::test_reject_float_bool_nonfinite_and_excessive_decimal_places[payload0]` (`1 failed`) | 🗑 Eliminado |
| `M1b` | Desactivar rechazo de `>2` decimales en `_parse_strict_decimal` (redondeo silencioso en `quantize`) | `app/modules/catalog/schemas.py` | `test_catalog_products.py::test_reject_float_bool_nonfinite_and_excessive_decimal_places[payload9]` (`1 failed`) | 🗑 Eliminado |
| `M1c` | Permitir `bool` en `_parse_strict_decimal` | `app/modules/catalog/schemas.py` | `test_catalog_products.py::test_reject_float_bool_nonfinite_and_excessive_decimal_places[payload3]` (`1 failed`) | 🗑 Eliminado |
| `M1d` | Desactivar validación `parsed.is_finite()` (`NaN` / `Infinity`) en `_parse_strict_decimal` | `app/modules/catalog/schemas.py` | `test_catalog_products.py::test_reject_float_bool_nonfinite_and_excessive_decimal_places[payload6]` (`1 failed`) | 🗑 Eliminado |
| `M1e` | Omitir `ge=Decimal("0")` en `ProductCreate.stock` (permitir stock negativo inicial) | `app/modules/catalog/schemas.py` | `test_catalog_products.py::test_reject_invalid_prices_negative_initial_stock_or_overflow[payload3]` (`1 failed`) | 🗑 Eliminado |
| `M1f` | Omitir `ge=Decimal("0")` en `ProductCreate.cost_price` | `app/modules/catalog/schemas.py` | `test_catalog_products.py::test_reject_invalid_prices_negative_initial_stock_or_overflow[payload2]` (`1 failed`) | 🗑 Eliminado |
| `M1g_full` | Omitir `le=MAX_NUMERIC_12_2` y `max_digits=12` en `ProductCreate.sale_price` | `app/modules/catalog/schemas.py` | `test_catalog_products.py::test_reject_invalid_prices_negative_initial_stock_or_overflow[payload6]` (`1 failed`) | 🗑 Eliminado |
| `M1h` | Omitir rechazo de `code` vacío o solo espacios en `ProductCreate.validate_code` | `app/modules/catalog/schemas.py` | `test_catalog_products.py::test_reject_blank_or_oversized_or_nul_byte_in_post_payload[payload2]` (`1 failed`) | 🗑 Eliminado |
| `M1i` | Omitir `reject_nul_byte(value)` en `ProductListQuery.validate_query` (parámetro `q`) | `app/modules/catalog/schemas.py` | `test_catalog_products.py::test_reject_nul_byte_in_search_query_parameter` (`1 failed`) | 🗑 Eliminado |
| `M1k_nul_post` | Omitir `reject_nul_byte(value)` en `ProductCreate.validate_name` y `validate_code` | `app/modules/catalog/schemas.py` | `test_catalog_products.py::test_reject_blank_or_oversized_or_nul_byte_in_post_payload[payload6]` (`1 failed`) | 🗑 Eliminado |
| `M1j1` | Omitir cotas `ge=1, le=200` en `ProductListQuery.limit` *(brecha previa)* | `app/modules/catalog/schemas.py` | `test_catalog_products.py::test_reject_invalid_list_query_bounds[query_params0]` (`1 failed`) | 🗑 Eliminado |
| `M1j2` | Omitir cota `ge=0` en `ProductListQuery.offset` *(brecha previa)* | `app/modules/catalog/schemas.py` | `test_catalog_products.py::test_reject_invalid_list_query_bounds[query_params3]` (`1 failed`) | 🗑 Eliminado |
| `M1j3` | Omitir `max_length=150` en `ProductListQuery.q` *(brecha previa)* | `app/modules/catalog/schemas.py` | `test_catalog_products.py::test_reject_invalid_list_query_bounds[query_params4]` (`1 failed`) | 🗑 Eliminado |
| `M2a` | Reemplazar `Depends(require_owner)` por `Depends(get_current_tenant)` en `POST /catalog/products` | `app/modules/catalog/router.py` | `test_catalog_products.py::test_product_creation_restricted_to_owner_cashier_gets_403` (`1 failed`) | 🗑 Eliminado |
| `M2b` | Desactivar guard `if current_user.role != "owner"` en `require_owner` | `app/core/security.py` | `test_catalog_products.py::test_product_creation_restricted_to_owner_cashier_gets_403` (`1 failed`) | 🗑 Eliminado |
| `M2c` | Omitir `401 UNAUTHENTICATED` cuando falta cookie en `get_current_user` | `app/core/security.py` | `test_catalog_products.py::test_unauthenticated_and_onboarding_pending_rejected` (`1 failed`) | 🗑 Eliminado |
| `M2d` | Omitir redacción de `cost_price` para `cashier` (`redact_cost = False`) en `CatalogService.list_products` | `app/modules/catalog/service.py` | `test_catalog_products.py::test_listing_redacts_cost_price_for_cashier_and_exposes_to_owner` (`1 failed`) | 🗑 Eliminado |
| `M2e` | Invertir redacción de `cost_price` (`redact_cost = current_user.role == "owner"`) en `CatalogService.list_products` | `app/modules/catalog/service.py` | `test_catalog_products.py::test_listing_redacts_cost_price_for_cashier_and_exposes_to_owner` (`1 failed`) | 🗑 Eliminado |
| `M2f_onb` | Desactivar guard `403 ONBOARDING_REQUIRED` en `get_current_tenant` y `get_tenant_db` | `app/core/security.py`, `app/core/db.py` | `test_catalog_products.py::test_unauthenticated_and_onboarding_pending_rejected` (`1 failed`) | 🗑 Eliminado |
| `M3a` | Reemplazar `Depends(get_tenant_db)` por `Depends(get_db)` en `get_catalog_service` | `app/modules/catalog/router.py` | `test_catalog_products.py::test_create_product_with_all_attributes` (`1 failed`) | 🗑 Eliminado |
| `M3b` | Omitir `set_rls_business_context(session, current_user.business_id)` en `get_tenant_db` | `app/core/db.py` | `test_catalog_products.py::test_create_product_with_all_attributes` (`1 failed`) | 🗑 Eliminado |
| `M3c` | Omitir `SET LOCAL ROLE app_api` en `set_rls_user_context` | `app/core/db.py` | `test_catalog_products.py::test_create_product_with_all_attributes` (`1 failed`) | 🗑 Eliminado |
| `M3d` | Permitir `business_id` en `ProductCreate` y priorizar `payload.business_id` sobre `current_user.business_id` (IDOR) | `app/modules/catalog/schemas.py`, `app/modules/catalog/service.py` | `test_catalog_products.py::test_tenant_isolation_rls_and_ignore_body_business_id` (`1 failed`) | 🗑 Eliminado |
| `M3e` | Omitir `set_config('app.current_user_id', ...)` en `set_rls_user_context` | `app/core/db.py` | `test_auth_onboarding.py::test_login_success_with_existing_business` (`1 failed` en suite completa `tests/`) | 🗑 Eliminado |
| `M4a` | Relajar `sale_price > 0` (`gt=Decimal("0")`) a `>= 0` (`ge=Decimal("0")`) en `ProductCreate` | `app/modules/catalog/schemas.py` | `test_catalog_products.py::test_reject_invalid_prices_negative_initial_stock_or_overflow[payload0]` (`1 failed`) | 🗑 Eliminado |
| `M4b1` | Quitar escape de comodines `%` y `_` en búsqueda `q` (`escaped = q`) | `app/modules/catalog/repository.py` | `test_catalog_products.py::test_search_products_case_insensitive_with_wildcard_escaping` (`1 failed`) | 🗑 Eliminado |
| `M4b2` | Quitar solo el escape de backslash `\` (`q.replace("\\", "\\\\")`) en búsqueda `q` *(brecha previa)* | `app/modules/catalog/repository.py` | `test_catalog_products.py::test_search_products_case_insensitive_with_wildcard_escaping` (`1 failed`) | 🗑 Eliminado |
| `M4c` | Cambiar `include_inactive` default de `False` a `True` en `ProductListQuery` | `app/modules/catalog/schemas.py` | `test_catalog_products.py::test_inactive_products_hidden_by_default_and_revealed_when_requested` (`1 failed`) | 🗑 Eliminado |
| `M4d` | Desactivar filtro `Product.is_active.is_(True)` en `CatalogRepository.list_products` | `app/modules/catalog/repository.py` | `test_catalog_products.py::test_inactive_products_hidden_by_default_and_revealed_when_requested` (`1 failed`) | 🗑 Eliminado |
| `M4e` | Omitir desempate `Product.id.asc()` en `.order_by(Product.name.asc())` | `app/modules/catalog/repository.py` | `test_catalog_products.py::test_list_active_products_ordered_deterministically_with_negative_stock` (`1 failed`) | 🗑 Eliminado |
| `M4f` | Buscar `q` únicamente sobre `Product.name` omitiendo `Product.code` | `app/modules/catalog/repository.py` | `test_catalog_products.py::test_search_products_case_insensitive_with_wildcard_escaping` (`1 failed`) | 🗑 Eliminado |
| `M4g` | Omitir `.where(*filters)` en `count_stmt` de `CatalogRepository.list_products` | `app/modules/catalog/repository.py` | `test_catalog_products.py::test_search_products_case_insensitive_with_wildcard_escaping` (`1 failed`) | 🗑 Eliminado |
| `M4h` | Omitir `.offset(offset)` en `items_stmt` de `CatalogRepository.list_products` | `app/modules/catalog/repository.py` | `test_catalog_products.py::test_blank_search_query_returns_full_catalog_with_pagination` (`1 failed`) | 🗑 Eliminado |
| `M4h2_limit` | Omitir `.limit(limit)` en `items_stmt` de `CatalogRepository.list_products` | `app/modules/catalog/repository.py` | `test_catalog_products.py::test_blank_search_query_returns_full_catalog_with_pagination` (`1 failed`) | 🗑 Eliminado |
| `M4i_nostrip` | Omitir `.strip()` en `ProductListQuery.validate_query` (`return value or None`) | `app/modules/catalog/schemas.py` | `test_catalog_products.py::test_blank_search_query_returns_full_catalog_with_pagination` (`1 failed`) | 🗑 Eliminado |
| `M4j` | Omitir `.strip()` en `ProductCreate.validate_name` | `app/modules/catalog/schemas.py` | `test_catalog_products.py::test_create_product_with_all_attributes` (`1 failed`) | 🗑 Eliminado |
| `M4k` | Sobre-restringir `stock: Decimal = Field(ge=Decimal("0"))` en `ProductResponse` | `app/modules/catalog/schemas.py` | `test_catalog_products.py::test_list_active_products_ordered_deterministically_with_negative_stock` (`1 failed`) | 🗑 Eliminado |
| `M5a` | Devolver `500 Internal Server Error` en lugar de `409 Conflict` ante `DuplicateProductCodeError` | `app/modules/catalog/router.py` | `test_catalog_products.py::test_create_duplicate_non_null_code_same_business_returns_409` (`1 failed`) | 🗑 Eliminado |
| `M5b` | Eliminar bloque `except DuplicateProductCodeError` en `router.py` (500 no manejado) | `app/modules/catalog/router.py` | `test_catalog_products.py::test_create_duplicate_non_null_code_same_business_returns_409` (`1 failed`) | 🗑 Eliminado |
| `M5c` | Alterar `"code": "PRODUCT_CODE_ALREADY_EXISTS"` a `"DUPLICATE_ERROR"` en `router.py` | `app/modules/catalog/router.py` | `test_catalog_products.py::test_create_duplicate_non_null_code_same_business_returns_409` (`1 failed`) | 🗑 Eliminado |
| `M5d` | Devolver `200 OK` en lugar de `409 Conflict` ante `DuplicateProductCodeError` | `app/modules/catalog/router.py` | `test_catalog_products.py::test_create_duplicate_non_null_code_same_business_returns_409` (`1 failed`) | 🗑 Eliminado |
| `M5e` | No convertir `IntegrityError` (`23505`) en `DuplicateProductCodeError` (`_is_duplicate_product_code_violation` retorna `False`) | `app/modules/catalog/service.py` | `test_catalog_products.py::test_create_duplicate_non_null_code_same_business_returns_409` (`1 failed`) | 🗑 Eliminado |
| `M5f` | Omitir `async with self._session.begin_nested():` (savepoint) en `CatalogRepository._transaction` *(brecha previa)* | `app/modules/catalog/repository.py` | `test_catalog_products.py::test_duplicate_code_409_uses_savepoint_and_keeps_outer_transaction_healthy` (`1 failed`) | 🗑 Eliminado |

### Mutantes Equivalentes Verificados (Excluidos del Denominador)

| Variante | Descripción | Por qué es Equivalente | Contraparte No Equivalente Probada |
|---|---|---|---|
| `M1g` | Omitir solo `le=MAX_NUMERIC_12_2` en `ProductCreate.sale_price` manteniendo `max_digits=12` | `_parse_strict_decimal` cuantiza siempre a `.01` (`2` decimales) antes de validar `Field(max_digits=12)`. Todo valor `>= 10000000000` cuantizado a `.01` posee `>= 13` dígitos y es rechazado igualmente por `max_digits=12` con `422`. | `M1g_full` (omite ambos) → **🗑 Eliminado** |
| `M4i` | Retornar `cleaned` (`""`) en lugar de `cleaned or None` en `ProductListQuery.validate_query` (manteniendo `.strip()`) | En `CatalogRepository.list_products`, la condición `if q:` evalúa tanto `""` como `None` como falsy, produciendo exactamente el mismo SQL y la misma respuesta HTTP. | `M4i_nostrip` (omite `.strip()`) → **🗑 Eliminado** |

---

## 3. Brechas de Falsabilidad y Acción Requerida

- **`[TESTS BLINDADOS]`:** Suite Backend-TDD verificada como robusta y falsable tras el refuerzo aplicado en `backend/tests/integration/test_catalog_products.py` (`54 passed`):
  - **Brechas 1, 2 y 3 cerradas (`M1j1`, `M1j2`, `M1j3`):** `test_reject_invalid_list_query_bounds` (`limit=0`, `limit=-1`, `limit=201`, `offset=-1`, `q="a"*151` → `422 VALIDATION_ERROR` sin consultar `products`) y `test_accept_valid_list_query_boundary_values` (`limit=1`, `limit=200`, `offset=0`, `q="a"*150` → `200 OK`) eliminan los 3 mutantes de cotas de `ProductListQuery`.
  - **Brecha 4 cerrada (`M4b2`):** `test_search_products_case_insensitive_with_wildcard_escaping` ahora siembra productos con `\` literal (`"Cable 2\\3"`, `"SKU\\01"`) y valida búsquedas con `q="2\\3"`, `q="sku\\01"` y `q="\\"`, atrapando la omisión del escape de backslash.
  - **Brecha 5 cerrada (`M5f`):** `test_duplicate_code_409_uses_savepoint_and_keeps_outer_transaction_healthy` ejecuta `POST` duplicado (`409`) dentro de una transacción externa activa compartida vía `get_tenant_db` override y comprueba que un `SELECT COUNT(*)` posterior sobre la misma `AsyncSession` se ejecuta limpiamente sin `InFailedSQLTransactionError`.
  - **Cobertura transversal (`M3e`):** `app.current_user_id` en `app/core/db.py` permanece validado en la suite completa por `tests/integration/test_auth_onboarding.py::test_login_success_with_existing_business`, mientras las políticas RLS de `products` dependen exclusivamente de `app.current_business_id` (verificado en `test_catalog_products.py`).
- Cambio listo para `opsx:archive`.
