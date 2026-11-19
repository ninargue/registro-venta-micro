## 1. Piezas Core Compartidas y DTOs de Catálogo (consumiendo `models.py` inmutable)

- [x] 1.1 Extraer `ErrorResponse` y el helper de rechazo de bytes NUL a `backend/app/core/schemas.py`, re-exportar `ErrorResponse` en `backend/app/modules/auth/schemas.py` para compatibilidad y actualizar la importación en `backend/app/main.py`
- [x] 1.2 Agregar la dependencia `require_owner` en `backend/app/core/security.py` sobre `get_current_tenant`, rechazando con HTTP 403 (`code = "FORBIDDEN"`) cualquier sesión cuyo `role` sea distinto de `"owner"`
- [x] 1.3 Implementar esquemas Pydantic v2 y validadores estrictos en `backend/app/modules/catalog/schemas.py` (`ProductCreate`, `ProductListQuery`, `ProductResponse`, `ProductListResponse`) con rechazo de `float`/`bool`/`NaN`/`Infinity`, escala máxima de 2 decimales, tope `numeric(12,2)` (`<= 9999999999.99`), `sale_price > 0`, `cost_price >= 0`, `stock >= 0` en alta (permitiendo `stock` negativo en respuesta), validación de `name`/`code` y rechazo de bytes NUL (`\x00`)

## 2. Repositorio de Catálogo bajo RLS

- [x] 2.1 Implementar `CatalogRepository` en `backend/app/modules/catalog/repository.py` consumiendo el modelo inmutable `Product` de `backend/app/modules/catalog/models.py`: método `create_product` con contexto `_transaction()` (`begin_nested()` savepoint) ejecutando `INSERT ... RETURNING Product` con `business_id` explícito del tenant
- [x] 2.2 Implementar `list_products` en `backend/app/modules/catalog/repository.py` aplicando filtros compartidos (`is_active` según `include_inactive`, búsqueda `q` case-insensitive en `name` y `code` con escape literal de `\`, `%` y `_`), conteo total exacto, orden determinista `name ASC, id ASC` y paginación `LIMIT`/`OFFSET`

## 3. Capa de Servicio de Catálogo

- [x] 3.1 Implementar `CatalogService` y la excepción `DuplicateProductCodeError` en `backend/app/modules/catalog/service.py` para el alta de productos, capturando `IntegrityError` (`sqlstate == "23505"` y constraint `uq_products_business_id_code`) hacia `DuplicateProductCodeError` sin envolver otros errores de integridad inesperados
- [x] 3.2 Implementar `list_products` en `backend/app/modules/catalog/service.py` construyendo `ProductListResponse` con serialización decimal cuantizada a 2 decimales y redacción de `cost_price = None` cuando el usuario autenticado tenga `role != "owner"`

## 4. Router FastAPI, Documentación OpenAPI y Registro en App

- [x] 4.1 Implementar `GET /api/v1/catalog/products` y `POST /api/v1/catalog/products` en `backend/app/modules/catalog/router.py` con `tags=["catalog"]`, dependencias `get_current_tenant` / `require_owner` + `get_tenant_db`, mapeo de `DuplicateProductCodeError` a `HTTPException(409, code="PRODUCT_CODE_ALREADY_EXISTS")` y documentación explícita de respuestas `200`/`201`/`401`/`403`/`409`/`422` (`ErrorResponse`) para OpenAPI
- [x] 4.2 Registrar `catalog_router` en `backend/app/main.py` bajo `prefix="/api/v1"` sin modificar `backend/migrations/` ni `backend/app/modules/catalog/models.py`

## 5. Pruebas de Dominio, Aislamiento RLS y Validación Determinista

- [ ] 5.1 Implementar pruebas unitarias de esquemas y contrato OpenAPI en `backend/tests/unit/test_catalog_schemas.py` cubriendo validación `Decimal` estricta, rechazo de `float`/`bool`/`NaN`/`Infinity`/escala `> 2`/overflow `numeric(12,2)`, rechazo de valores inválidos, bytes NUL, trim de `name`/`code`, `stock` negativo en `ProductResponse` y documentación de rutas/esquemas en `/openapi.json`
- [x] 5.2 Implementar pruebas de integración y aislamiento RLS en `backend/tests/integration/test_catalog_products.py` cubriendo todos los escenarios de `specs/catalog-products-api/spec.md`: alta completa y con defaults (`201`), múltiples `code=null` (`201`), mismo `code` entre distintos comercios (`201`), `code` duplicado en mismo comercio (`409` con `ErrorResponse` y sesión intacta), listado ordenado y paginado (`200`), búsqueda con escape de `%`/`_`, `include_inactive`, `401`/`403` sin sesión o sin onboarding, `403` para `cashier` en `POST`, redacción de `cost_price` para `cashier` en `GET`, aislamiento RLS entre comercios e ignorado de `business_id` en el body
- [ ] 5.3 Ejecutar validación de calidad y pruebas completas (`cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy app && uv run pytest`) confirmando 0 cambios en `backend/migrations/` y `backend/app/modules/catalog/models.py`
