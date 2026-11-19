# Verification Report: `us-02-t04b-backend`

- **Ticket / Issue:** `US-02-T04b` — [Issue #67](https://github.com/ninargue/registro-venta-micro/issues/67) (`PATCH /api/v1/catalog/products/{product_id}`)
- **Worktree verificado:** `C:\Users\Armenta\Documents\Repositories\wt-67-patch-endpoint-edicion-productos`
- **Agente:** `backend-qa-agent` (Fase B — `opsx:verify`)
- **Fecha:** 2026-11-19
- **Veredicto:** **[APROBADO]**

---

## 1. Summary Scorecard (`opsx:verify`)

| Dimension | Status | Detalle |
|---|---|---|
| **Completeness** | **PASS** (`9/9` tasks, `4/4` requirements) | Todas las tareas en `tasks.md` están marcadas `- [x]` y verificadas contra el código fuente. El 100% de los requisitos de `specs/catalog-products-api/spec.md` están implementados. |
| **Correctness** | **PASS** (`15/15` scenarios, `179/179` catalog tests, `302/302` total tests) | Los 15 escenarios Given/When/Then de `spec.md` están cubiertos por pruebas unitarias (`test_catalog_schemas.py`) y de integración RLS contra PostgreSQL 17 (`test_catalog_products.py`), pasando al 100% en VERDE (`93%` coverage global). |
| **Coherence** | **PASS** (`0` drift, `No-DB-Diff`, `export_openapi --check` exit `0`) | Adherencia 1:1 a `design.md` y `docs/api/openapi.json`. `backend/migrations/` y `backend/app/modules/catalog/models.py` permanecen 100% inmutables. Auditoría anti-bypass RLS superada (`SET LOCAL ROLE app_api`). |

---

## 2. Matriz Técnica de Gates Deterministas (Gates 1–4) y Cierre Fuera del Código

| Gate / Verificación | Estado | Evidencia Determinista |
|---|---|---|
| **Gate 1 — Compilación, Tipos y Lint** | **PASS** | `ruff check .` (`exit 0`), `ruff format --check .` (`exit 0`), `mypy app` (`exit 0`). |
| **Gate 2 — Pruebas Rápidas / Unitarias** | **PASS** | `tests/unit/test_catalog_schemas.py` en VERDE validando `ProductUpdate`, `UPDATABLE_PRODUCT_FIELDS`, precisión `Decimal`, rechazo de `null` en campos obligatorios y rechazo de `{}`. |
| **Gate 3 — Inmutabilidad de BD y Seguridad RLS** | **PASS** | `0` modificaciones en `backend/migrations/` y `backend/app/modules/catalog/models.py` (`No-DB-Diff`). Advertencia heurística de `service_role` auditada y descartada (corresponde únicamente a un comentario preventivo en `backend/app/core/config.py:23`). |
| **Gate 4 — Suite Completa e Inmutabilidad de Tests** | **PASS** | `validate-backend.js --gate 4` aprobado con `exit 0`. Huella de tests congelados intacta (`digest 468e486dc881`). `302 passed` en `pytest` (`93%` coverage global; `179 passed` en `test_catalog_schemas.py` + `test_catalog_products.py`). |
| **Verificación Fuera del Código (OpenAPI Drift Check)** | **PASS** | `uv run --directory backend python -m app.scripts.export_openapi --check` ejecutado en Fase B con `exit 0`: `docs/api/openapi.json` coincide exactamente con el esquema vivo de FastAPI (`GET /openapi.json`). |

---

## 3. Auditoría de Seguridad y Aislamiento Multi-Tenant (`rls_mode: in-situ`, `auth_mode: jwt`)

1. **Auditoría de la advertencia Gate 3 (`service_role` en `backend/app/core/config.py`):**
   - En `backend/app/core/config.py:23` la cadena `service_role` aparece exclusivamente en el comentario `# Supabase Auth (prohibido usar service_role en flujos de usuario).` y la clase `Settings` solo expone `supabase_url` y `supabase_anon_key`.
   - Ningún módulo de `backend/app/` (incluyendo `catalog`) instancia clientes ni conexiones con `service_role` ni privilegios `BYPASSRLS`.
2. **Contexto Transaccional RLS en `get_tenant_db` (`backend/app/core/db.py:41-94`):**
   - `PATCH /api/v1/catalog/products/{product_id}` inyecta `current_user: CurrentUser = Depends(require_owner)` (`backend/app/modules/catalog/router.py:98`) y `service: CatalogService = Depends(get_catalog_service)` que depende de `get_tenant_db` (`backend/app/modules/catalog/router.py:27-31`).
   - `get_tenant_db` abre una transacción y ejecuta `SET LOCAL ROLE app_api`, `SELECT set_config('app.current_user_id', :user_id, true)` y `SELECT set_config('app.current_business_id', :business_id, true)`.
   - Verificado mediante captura de sentencias SQL (`_capture_sql_statements`) en `test_patch_product_partial_update_preserves_omitted_fields_including_negative_stock` (`test_catalog_products.py:1299-1304`) y `test_patch_cross_tenant_product_id_returns_404_and_leaves_target_unmodified` (`test_catalog_products.py:1817-1822`).
3. **Defensa en Profundidad contra IDOR y Mutación de Metadatos:**
   - `ProductUpdate` ignora campos extra (`extra="ignore"`) y `CatalogService.update_product` (`service.py:105-108`) filtra explícitamente el diccionario con `UPDATABLE_PRODUCT_FIELDS = frozenset({"code", "name", "sale_price", "cost_price", "stock"})`.
   - `CatalogRepository.update_product` (`repository.py:66-70`) valida que `updates` no sea vacío ni contenga llaves fuera de `UPDATABLE_PRODUCT_FIELDS`, y ejecuta `UPDATE products SET ... WHERE products.id = :product_id AND products.business_id = :business_id RETURNING *` dentro de `self._transaction()` (`begin_nested()` savepoint).
   - Un intento de editar un `product_id` perteneciente a otro tenant bajo `SET LOCAL ROLE app_api` afecta `0` filas y devuelve HTTP `404 Not Found` (`code = "PRODUCT_NOT_FOUND"`), sin revelar la existencia del recurso ni modificar los datos del tenant víctima.

---

## 4. Evaluaciones Detalladas por Dimensión

### 4.1. Completeness (Completitud)

#### Verificación de Tareas (`tasks.md`)
- [x] **1.1** Helpers compartidos `_validate_optional_code` y `_validate_product_name` extraídos en `backend/app/modules/catalog/schemas.py:18-39` y reutilizados por `ProductCreate` y `ProductUpdate`.
- [x] **1.2** `UPDATABLE_PRODUCT_FIELDS` y `ProductUpdate` implementados en `backend/app/modules/catalog/schemas.py:12-15, 137-205` con validación `Decimal` estricta, limpieza de `code: null`, rechazo de `null` en campos no nulables, rechazo de `{}` y rechazo de `\x00`.
- [x] **2.1** `CatalogRepository.update_product` implementado en `backend/app/modules/catalog/repository.py:58-80` con `UPDATE ... WHERE id = :product_id AND business_id = :business_id RETURNING Product` bajo savepoint `_transaction()` y whitelist `UPDATABLE_PRODUCT_FIELDS`.
- [x] **3.1** `ProductNotFoundError` y `CatalogService.update_product` implementados en `backend/app/modules/catalog/service.py:24-25, 95-126` usando `model_dump(exclude_unset=True)`, mapeando `23505` (`uq_products_business_id_code`) a `DuplicateProductCodeError` y `None` a `ProductNotFoundError`.
- [x] **4.1** Endpoint `PATCH /api/v1/catalog/products/{product_id}` implementado en `backend/app/modules/catalog/router.py:83-121` con `require_owner`, `get_tenant_db`, y respuestas `200`, `401`, `403`, `404`, `409` y `422`.
- [x] **4.2** Contrato estático `docs/api/openapi.json` actualizado (`openapi.json:450-543, 932-1031`) y verificado con `export_openapi --check` (`exit 0`).
- [x] **5.1** Pruebas unitarias de `ProductUpdate` añadidas en `backend/tests/unit/test_catalog_schemas.py:103-229`.
- [x] **5.2** Pruebas de integración y aislamiento RLS de `PATCH /api/v1/catalog/products/{product_id}` añadidas en `backend/tests/integration/test_catalog_products.py:1240-1930`.
- [x] **5.3** Validación integral de calidad, tipos, tests y contrato OpenAPI superada con 0 cambios en `backend/migrations/` y `backend/app/modules/catalog/models.py`.

#### Cobertura de Requisitos (`specs/catalog-products-api/spec.md`)
1. **Requirement: Partial Product Update via Catalog Endpoint** → Implementado en `router.py:83-121`, `service.py:95-126`, `repository.py:58-80`.
2. **Requirement: Strict Decimal Precision and Partial Payload Validation on Product Update** → Implementado en `schemas.py:12-76, 137-205`.
3. **Requirement: Authorization, Multi-Tenant RLS Isolation, and 404 Semantics on Product Update** → Implementado en `router.py:83-112`, `security.py:183-212`, `db.py:77-94`, `repository.py:58-80`.
4. **Requirement: OpenAPI Contract Documentation and Static Synchronization for Product Update** → Implementado en `router.py:83-94` y sincronizado en `docs/api/openapi.json:450-543, 932-1031`.

---

### 4.2. Correctness (Trazabilidad `Scenario -> Test`)

| # | Requisito en `spec.md` | Escenario (`#### Scenario:`) | Funciones de Test (`test_catalog_schemas.py` / `test_catalog_products.py`) | Estado |
|---|---|---|---|---|
| 1 | Partial Product Update via Catalog Endpoint | **Successful partial update of a subset of attributes preserves omitted fields** | `test_catalog_schemas.py::test_product_update_partial_payload_and_exclude_unset` (L109-120)<br/>`test_catalog_products.py::test_patch_product_partial_update_preserves_omitted_fields_including_negative_stock` (L1240-1333) | **VERDE** |
| 2 | Partial Product Update via Catalog Endpoint | **Successful update of all editable attributes including clearing optional code to null** | `test_catalog_schemas.py::test_product_update_full_payload_and_explicit_null_code` (L123-140)<br/>`test_catalog_products.py::test_patch_product_all_editable_attributes_and_clear_code_to_null` (L1336-1391) | **VERDE** |
| 3 | Partial Product Update via Catalog Endpoint | **Updating a product keeping its own code or matching a code from another business succeeds** | `test_catalog_products.py::test_patch_product_keeping_own_code_or_matching_another_business_code_succeeds` (L1394-1449) | **VERDE** |
| 4 | Partial Product Update via Catalog Endpoint | **Updating code to an existing non-null code in the same business returns 409 Conflict** | `test_catalog_products.py::test_patch_product_duplicate_code_same_business_returns_409_and_uses_savepoint` (L1452-1522) | **VERDE** |
| 5 | Strict Decimal Precision and Partial Payload Validation on Product Update | **Rejection of float, bool, non-finite decimals, excessive decimal places, and numeric overflow on update** | `test_catalog_schemas.py::test_product_update_rejects_invalid_decimal_inputs` (L169-193)<br/>`test_catalog_products.py::test_patch_rejects_float_bool_nonfinite_excessive_decimals_and_overflow` (L1525-1571) | **VERDE** |
| 6 | Strict Decimal Precision and Partial Payload Validation on Product Update | **Rejection of non-positive sale_price, negative cost_price, or negative stock on update** | `test_catalog_schemas.py::test_product_update_rejects_out_of_range_bounds` (L196-208)<br/>`test_catalog_products.py::test_patch_rejects_non_positive_sale_price_negative_cost_or_negative_stock` (L1574-1607) | **VERDE** |
| 7 | Strict Decimal Precision and Partial Payload Validation on Product Update | **Rejection of explicit null on non-nullable fields or empty update payload** | `test_catalog_schemas.py::test_product_update_rejects_empty_payload_or_only_ignored_fields` (L154-159)<br/>`test_catalog_schemas.py::test_product_update_rejects_explicit_null_on_non_nullable_fields` (L162-166)<br/>`test_catalog_products.py::test_patch_rejects_explicit_null_on_non_nullable_fields_or_empty_payload` (L1610-1643) | **VERDE** |
| 8 | Strict Decimal Precision and Partial Payload Validation on Product Update | **Rejection of blank strings, oversized strings, NUL bytes, or invalid product_id UUID** | `test_catalog_schemas.py::test_product_update_rejects_blank_oversized_and_nul_byte_strings` (L211-229)<br/>`test_catalog_products.py::test_patch_rejects_blank_oversized_nul_bytes_or_invalid_product_id_uuid` (L1646-1684) | **VERDE** |
| 9 | Authorization, Multi-Tenant RLS Isolation, and 404 Semantics on Product Update | **Unauthenticated or onboarding-pending update requests rejected with 401 and 403** | `test_catalog_products.py::test_patch_unauthenticated_and_onboarding_pending_rejected_with_401_and_403` (L1687-1713) | **VERDE** |
| 10 | Authorization, Multi-Tenant RLS Isolation, and 404 Semantics on Product Update | **Cashier role rejected with 403 Forbidden on product update** | `test_catalog_products.py::test_patch_cashier_role_rejected_with_403_forbidden` (L1716-1749) | **VERDE** |
| 11 | Authorization, Multi-Tenant RLS Isolation, and 404 Semantics on Product Update | **Non-existent product_id returns 404 Not Found** | `test_catalog_products.py::test_patch_non_existent_product_id_returns_404` (L1752-1778) | **VERDE** |
| 12 | Authorization, Multi-Tenant RLS Isolation, and 404 Semantics on Product Update | **Cross-tenant product_id returns 404 Not Found without leaking existence or mutating data** | `test_catalog_products.py::test_patch_cross_tenant_product_id_returns_404_and_leaves_target_unmodified` (L1781-1843) | **VERDE** |
| 13 | Authorization, Multi-Tenant RLS Isolation, and 404 Semantics on Product Update | **Client-supplied business_id or immutable metadata fields in payload are ignored** | `test_catalog_schemas.py::test_product_update_trims_code_and_ignores_extra_immutable_fields` (L143-151)<br/>`test_catalog_products.py::test_patch_ignores_client_supplied_business_id_and_immutable_fields` (L1846-1900) | **VERDE** |
| 14 | OpenAPI Contract Documentation and Static Synchronization for Product Update | **PATCH catalog route and ProductUpdate schema documented in live and static OpenAPI contracts** | `test_catalog_products.py::test_openapi_documents_patch_catalog_route_and_product_update_schema` (L1903-1930) + `export_openapi --check` (`exit 0`) | **VERDE** |
| 15 | OpenAPI Contract Documentation and Static Synchronization for Product Update | **All error responses on product update conform to uniform ErrorResponse format** | Verificado transversalmente mediante `_assert_uniform_error_response` (`set(body.keys()) == {"code", "message", "details"}`) en todos los tests `401`, `403`, `404`, `409` y `422` de `PATCH` (`test_catalog_products.py:1504, 1570, 1606, 1642, 1683, 1711, 1712, 1746, 1776, 1816`) | **VERDE** |

---

### 4.3. Coherence (Drift Check 1:1 `design.md` & `openapi.json` vs Código)

| Componente / Contrato | Especificado en `design.md` / `docs/api/openapi.json` | Implementado en `backend/app/modules/catalog/` | Drift |
|---|---|---|---|
| **Endpoint & Método** | `PATCH /api/v1/catalog/products/{product_id}` (`tags=["catalog"]`, parameter `product_id: uuid`) | `@router.patch("/products/{product_id}", ...)` bajo `APIRouter(prefix="/catalog", tags=["catalog"])` (`router.py:24, 83-96`) | **0 Drift** |
| **Guards de Auth / RBAC / RLS** | `require_owner` + `get_tenant_db` (`SET LOCAL ROLE app_api`, `app.current_user_id`, `app.current_business_id`) | `current_user: CurrentUser = Depends(require_owner)` + `get_catalog_service(db=Depends(get_tenant_db))` (`router.py:27-31, 98-99`) | **0 Drift** |
| **Request Schema (`ProductUpdate`)** | `code`, `name`, `sale_price`, `cost_price`, `stock` opcionales; `UPDATABLE_PRODUCT_FIELDS`; `_validate_optional_code`, `_validate_product_name`, `_parse_strict_decimal`; `@model_validator(mode="after")` contra `{}` y `null` en campos obligatorios | Exactamente implementado en `schemas.py:12-15, 18-76, 137-205` y reflejado en `docs/api/openapi.json:932-1031` | **0 Drift** |
| **Response Schema (`200 OK`)** | `ProductResponse` (`id`, `code`, `name`, `sale_price`, `cost_price`, `stock`, `is_active`, `created_at`, `updated_at`) sin filtrar `cost_price` para `owner` ni exponer `business_id` | `response_model=ProductResponse`, `status_code=status.HTTP_200_OK`, `self._to_product_response(product, redact_cost=False)` (`router.py:85-86`, `service.py:126`) | **0 Drift** |
| **Status Codes & Error Codes** | `401` (`UNAUTHENTICATED`), `403` (`ONBOARDING_REQUIRED` / `FORBIDDEN`), `404` (`PRODUCT_NOT_FOUND`), `409` (`PRODUCT_CODE_ALREADY_EXISTS`), `422` (`VALIDATION_ERROR`) con `ErrorResponse` | Documentados en `responses={401, 403, 404, 409, 422}` (`router.py:87-93`) y mapeados desde `ProductNotFoundError` (`404`) y `DuplicateProductCodeError` (`409`) (`router.py:104-121`) | **0 Drift** |
| **Repositorio & Savepoint** | `UPDATE products SET ... WHERE id = :product_id AND business_id = :business_id RETURNING Product` dentro de `_transaction()` (`begin_nested()`) | Exactamente implementado en `repository.py:58-80` | **0 Drift** |
| **Inmutabilidad de BD (`No-DB-Diff`)** | Sin cambios en `backend/migrations/` ni en `backend/app/modules/catalog/models.py` | Confirmado en Gate 3 y revisión de `models.py` | **0 Drift** |

---

## 5. Issues by Priority

### CRITICAL (Must fix before archive)
- *(Ninguno)*

### WARNING (Should fix)
- *(Ninguno)*

### SUGGESTION (Nice to fix)
- *(Ninguna)*

---

## 6. Final Assessment

**All checks passed. Ready for archive.**

- **Veredicto Final:** **[APROBADO]**
