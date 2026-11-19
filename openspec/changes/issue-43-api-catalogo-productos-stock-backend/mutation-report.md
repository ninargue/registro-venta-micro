# 🔬 REPORTE DE MUTATION TESTING Y FALSABILIDAD: issue-43-api-catalogo-productos-stock-backend

## 1. Veredicto de Falsabilidad
- **Estado:** `[TESTS COMPLACIENTES DETECTADOS]`
- **Modo de Ejecución:** `Catálogo Canónico M1–M5` (`mutation_cmd: none` en `design.md`; ejecutado sobre copia temporal aislada en `$env:TEMP\mut_catalog_43` con `uv run --project C:\Users\Armenta\Documents\Repositories\wt-43-api-catalogo-productos-stock\backend` y `PYTHONPATH` apuntando a la copia temporal; árbol vivo de `backend/app/` y `backend/tests/` intacto y copia temporal eliminada al finalizar, `TMP_EXISTS=False`)
- **Tests Auditados:** `backend/tests/integration/test_catalog_products.py` (`45 passed` en baseline aislado) y verificación cruzada de sobrevivientes contra la suite completa `backend/tests/` (`138 passed` en baseline según `verification-report.md` y verificado en las corridas de sobrevivientes)
- **Tasa de Mutantes Eliminados:**
  - **En `tests/integration/test_catalog_products.py` (variantes no equivalentes):** `38/44` (`86.4%`) eliminadas — `6` sobrevivientes (`M1j1`, `M1j2`, `M1j3`, `M3e`, `M4b2`, `M5f`).
  - **Contra la suite completa `tests/` (variantes no equivalentes):** `39/44` (`88.6%`) eliminadas (`M3e` es atrapado por `tests/integration/test_auth_onboarding.py::test_login_success_with_existing_business`) — **`5` sobrevivientes globales (`M1j1`, `M1j2`, `M1j3`, `M4b2`, `M5f`)**.
  - **Categorías canónicas `M1–M5`:** `2/5` completamente blindadas (`M2` y `M3` en suite completa), `3/5` con brechas (`M1`, `M4`, `M5`).
  - **Mutantes equivalentes excluidos del denominador (comprobados aparte):** `2` (`M1g` y `M4i`, cuyas contrapartes no equivalentes `M1g_full` y `M4i_nostrip` sí fueron eliminadas).

---

## 2. Matriz de Mutaciones Evaluadas

### Resumen Canónico M1–M5

| ID | Mutación | Archivo(s) Mutado(s) (`backend/app`) | Archivo de Test (`backend/tests`) | ¿Atrapó el Fallo? | Resultado |
|---|---|---|---|---|---|
| M1 | Eliminación/relajación de validación de entrada (`Decimal`, `float`, `bool`, `NaN`/`Inf`, >2 decimales, `stock >= 0`, `cost_price >= 0`, overflow, `\x00`, `code` vacío, cotas de `ProductListQuery`) | `app/modules/catalog/schemas.py` | `tests/integration/test_catalog_products.py` | Parcial (`11/14` no equivalentes) | ⚠️ Parcial (3 brechas: `M1j1`, `M1j2`, `M1j3`) |
| M2 | Inversión u omisión de guard RBAC/auth (`require_owner`, `get_current_user`, `get_current_tenant` + `get_tenant_db`, redacción de `cost_price` para `cashier`) | `app/modules/catalog/router.py`, `app/modules/catalog/service.py`, `app/core/security.py`, `app/core/db.py` | `tests/integration/test_catalog_products.py` | Sí (`6/6` variantes) | 🗑 Eliminado |
| M3 | Omisión de propagación RLS (`get_tenant_db`, `SET LOCAL ROLE app_api`, `app.current_business_id`, `app.current_user_id`) o IDOR vía `business_id` del payload | `app/modules/catalog/router.py`, `app/core/db.py`, `app/modules/catalog/schemas.py`, `app/modules/catalog/service.py` | `tests/integration/test_catalog_products.py` + `tests/integration/test_auth_onboarding.py` | Parcial en catalog (`4/5`); Completo en suite (`5/5`) | 🗑 Eliminado en suite (`M3e` cubierto en `auth`; brecha local en `catalog`) |
| M4 | Mutación de operador/límite de dominio (`sale_price > 0` → `>= 0`, `include_inactive`, `order_by`, escape `%`/`_`/`\`, paginación, `count`, `strip`, `stock` negativo) | `app/modules/catalog/schemas.py`, `app/modules/catalog/repository.py` | `tests/integration/test_catalog_products.py` | Parcial (`12/13` no equivalentes) | ⚠️ Parcial (1 brecha: `M4b2`) |
| M5 | Enmascaramiento de `DuplicateProductCodeError` / `23505` (`200`/`500` o código distinto en lugar de `409 Conflict`) y omisión de savepoint `begin_nested()` | `app/modules/catalog/router.py`, `app/modules/catalog/service.py`, `app/modules/catalog/repository.py` | `tests/integration/test_catalog_products.py` | Parcial (`5/6` variantes) | ⚠️ Parcial (1 brecha: `M5f`) |

---

### Detalle de Variantes Evaluadas en Entorno Aislado (Ejecución Fail-Fast `-x`)

Baseline verificado en la copia temporal aislada antes de mutar: `45 passed, 53 warnings in 24.22s` (`tests/integration/test_catalog_products.py`).

| Variante | Descripción de la Mutación | Archivo Mutado | Primer Test que Atrapó el Fallo (`-x`) / Resultado | Estado |
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
| `M1j1` | Omitir cotas `ge=1, le=200` en `ProductListQuery.limit` | `app/modules/catalog/schemas.py` | `45 passed` en `test_catalog_products.py` / `138 passed` en `tests/` | 🧟 **Sobrevivió** |
| `M1j2` | Omitir cota `ge=0` en `ProductListQuery.offset` | `app/modules/catalog/schemas.py` | `45 passed` en `test_catalog_products.py` / `138 passed` en `tests/` | 🧟 **Sobrevivió** |
| `M1j3` | Omitir `max_length=150` en `ProductListQuery.q` | `app/modules/catalog/schemas.py` | `45 passed` en `test_catalog_products.py` / `138 passed` en `tests/` | 🧟 **Sobrevivió** |
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
| `M3e` | Omitir `set_config('app.current_user_id', ...)` en `set_rls_user_context` | `app/core/db.py` | Sobrevive en `test_catalog_products.py` (`45 passed`); abatido en `tests/` por `test_auth_onboarding.py::test_login_success_with_existing_business` (`1 failed`) | ⚠️ Cubierto fuera de `catalog` |
| `M4a` | Relajar `sale_price > 0` (`gt=Decimal("0")`) a `>= 0` (`ge=Decimal("0")`) en `ProductCreate` | `app/modules/catalog/schemas.py` | `test_catalog_products.py::test_reject_invalid_prices_negative_initial_stock_or_overflow[payload0]` (`1 failed`) | 🗑 Eliminado |
| `M4b1` | Quitar escape de comodines `%` y `_` en búsqueda `q` (`escaped = q`) | `app/modules/catalog/repository.py` | `test_catalog_products.py::test_search_products_case_insensitive_with_wildcard_escaping` (`1 failed`) | 🗑 Eliminado |
| `M4b2` | Quitar solo el escape de backslash `\` (`q.replace("\\", "\\\\")`) en búsqueda `q` | `app/modules/catalog/repository.py` | `45 passed` en `test_catalog_products.py` / `138 passed` en `tests/` | 🧟 **Sobrevivió** |
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
| `M5f` | Omitir `async with self._session.begin_nested():` (savepoint) en `CatalogRepository._transaction` | `app/modules/catalog/repository.py` | `45 passed` en `test_catalog_products.py` / `138 passed` en `tests/` | 🧟 **Sobrevivió** |

### Mutantes Equivalentes Verificados (Excluidos del Denominador)

| Variante | Descripción | Por qué es Equivalente | Contraparte No Equivalente Probada |
|---|---|---|---|
| `M1g` | Omitir solo `le=MAX_NUMERIC_12_2` en `ProductCreate.sale_price` manteniendo `max_digits=12` | `_parse_strict_decimal` cuantiza siempre a `.01` (`2` decimales) antes de validar `Field(max_digits=12)`. Todo valor `>= 10000000000` cuantizado a `.01` posee `>= 13` dígitos y es rechazado igualmente por `max_digits=12` con `422`. | `M1g_full` (omite ambos) → **🗑 Eliminado** |
| `M4i` | Retornar `cleaned` (`""`) en lugar de `cleaned or None` en `ProductListQuery.validate_query` (manteniendo `.strip()`) | En `CatalogRepository.list_products`, la condición `if q:` evalúa tanto `""` como `None` como falsy, produciendo exactamente el mismo SQL y la misma respuesta HTTP. | `M4i_nostrip` (omite `.strip()`) → **🗑 Eliminado** |

---

## 3. Brechas de Falsabilidad y Acción Requerida

Se emite **`[TESTS COMPLACIENTES DETECTADOS]`** porque **5 mutantes no equivalentes sobrevivieron** a toda la suite (`138 passed`) y **1 mutante adicional de RLS (`M3e`)** no es verificado en `test_catalog_products.py`:

1. **Brecha 1 (`M1j1` — Cotas de `limit` en `GET /api/v1/catalog/products`):**
   - *Requisito incumplido sin ser detectado:* `specs/catalog-products-api/spec.md` exige `bounded limit (1..200, default 50)` y `design.md` define `limit: int = Field(default=50, ge=1, le=200)`.
   - *Por qué sobrevivió:* Ningún test en `backend/tests/` envía `limit=0`, `limit=-1` o `limit=201` esperando `422 VALIDATION_ERROR`. Si se eliminan `ge=1, le=200`, un cliente podría solicitar `limit=100000` o `limit=-1` (error `500` en PostgreSQL).
   - *Refuerzo sugerido:* Agregar pruebas parametrizadas en `tests/integration/test_catalog_products.py` (y/o `tests/unit/test_catalog_schemas.py`) verificando `422 VALIDATION_ERROR` para `limit=0`, `limit=-1`, `limit=201` y aceptación `200` en límites válidos `limit=1` y `limit=200`.

2. **Brecha 2 (`M1j2` — Cota inferior de `offset` en `GET /api/v1/catalog/products`):**
   - *Requisito incumplido sin ser detectado:* `specs/catalog-products-api/spec.md` exige `offset (>= 0, default 0)` y `design.md` define `offset: int = Field(default=0, ge=0)`.
   - *Por qué sobrevivió:* Ningún test envía `offset=-1` esperando `422 VALIDATION_ERROR`; sin `ge=0`, `offset=-1` llegaría hasta PostgreSQL provocando error `500` (`OFFSET must not be negative`).
   - *Refuerzo sugerido:* Agregar caso `offset=-1` esperando `422 VALIDATION_ERROR` (con aserción de que no se ejecutó consulta `FROM products`).

3. **Brecha 3 (`M1j3` — Longitud máxima `max_length=150` en parámetro `q`):**
   - *Contrato sin cobertura:* `design.md` define `q: str | None = Field(default=None, max_length=150)` en `ProductListQuery`.
   - *Por qué sobrevivió:* No existe test con `q` de longitud `> 150` (p. ej. `"a" * 151`) esperando `422 VALIDATION_ERROR`.
   - *Refuerzo sugerido:* Agregar caso `q="a" * 151` en `tests/integration/test_catalog_products.py` o `tests/unit/test_catalog_schemas.py`.

4. **Brecha 4 (`M4b2` — Escape de backslash literal `\` en búsqueda `q`):**
   - *Contrato sin cobertura:* `design.md` especifica escapar `\`, `%` y `_` (`q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")`) y `spec.md` exige `SQL LIKE/ILIKE wildcard escaping`.
   - *Por qué sobrevivió:* `test_search_products_case_insensitive_with_wildcard_escaping` prueba `%` (`"10%"`) y `_` (`"sku_01"`), pero nunca un literal `\`. Si se omite `.replace("\\", "\\\\")`, consultar `q="10\\"` o `q="A\\B"` falla con SQLSTATE `22025` (`LIKE` invalid escape string → `500`) o interpreta `\` como carácter de escape en lugar de literal.
   - *Refuerzo sugerido:* Sembrar un producto con `\` en `name` o `code` (p. ej. `"Cable 2\\3"` / `"SKU\\01"`) y verificar búsqueda literal `q="2\\3"` y `q="10\\"` devolviendo `200 OK` sin error `500`.

5. **Brecha 5 (`M5f` — Savepoint `begin_nested()` en `CatalogRepository._transaction`):**
   - *Contrato sin falsabilidad:* `design.md` (Decisión #5 y §4) diseña `_transaction()` con `begin_nested()` cuando `self._session.in_transaction()` es verdadero para evitar `InFailedSQLTransactionError` al capturar `IntegrityError` (`23505`) dentro de una transacción abierta.
   - *Por qué sobrevivió:* `test_create_duplicate_non_null_code_same_business_returns_409` valida la recuperación haciendo un segundo request HTTP (`GET`), el cual recibe una nueva `AsyncSession` de `get_tenant_db`, mientras que `HTTPException(409)` ya había disparado `rollback()` automático en el teardown de la primera petición. Por tanto, el savepoint `begin_nested()` nunca es ejercitado en una sesión compartida.
   - *Refuerzo sugerido:* Agregar una prueba unitaria/integración sobre `CatalogRepository` (o `CatalogService`) dentro de una transacción activa (`async with db_session.begin():`) donde tras capturar `IntegrityError` / `DuplicateProductCodeError` por código duplicado se ejecute un `SELECT` sobre la misma `db_session` comprobando que la transacción externa no quedó abortada (`InFailedSQLTransactionError`).

6. **Observación menor en alcance de catálogo (`M3e` — `app.current_user_id` en `test_catalog_products.py`):**
   - `M3e` sobrevive si se corre únicamente `test_catalog_products.py` (aunque es eliminado en la suite completa por `test_auth_onboarding.py::test_login_success_with_existing_business`), dado que `test_catalog_products.py` verifica `SET LOCAL ROLE app_api` y `app.current_business_id`, pero no `app.current_user_id` mencionado en `design.md`. Si se desea blindar el archivo de catálogo de forma autónoma, puede agregarse esa aserción en `_capture_sql_statements()`.

- **Siguiente paso recomendado:** Re-despachar a `backend-test-writer-agent` (con este reporte) para reforzar las aserciones de `M1j1`, `M1j2`, `M1j3`, `M4b2` y `M5f` (y opcionalmente `M3e` / `tests/unit/test_catalog_schemas.py`), re-congelar huella de tests, re-validar Gate 4 y re-ejecutar Paso 5 hasta alcanzar `[TESTS BLINDADOS]`.
