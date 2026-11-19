## 1. Esquemas Pydantic y Validadores de Catálogo (consumiendo `models.py` inmutable)

- [x] 1.1 Extraer los helpers compartidos `_validate_optional_code` y `_validate_product_name` en `backend/app/modules/catalog/schemas.py` para reutilizarlos entre `ProductCreate` y `ProductUpdate` sin duplicar lógica
- [x] 1.2 Implementar `UPDATABLE_PRODUCT_FIELDS` y el esquema Pydantic v2 `ProductUpdate` en `backend/app/modules/catalog/schemas.py` con campos opcionales (`code`, `name`, `sale_price`, `cost_price`, `stock`), validación estricta en `Decimal` (sin `float`/`bool`/`NaN`/`Infinity`/escala `> 2`/overflow `numeric(12,2)`), `sale_price > 0`, `cost_price >= 0`, `stock >= 0`, limpieza explícita de `code: null`, rechazo de `null` en campos obligatorios (`name`, `sale_price`, `cost_price`, `stock`), rechazo de payloads vacíos (`{}` o sin campos editables) y rechazo de bytes NUL (`\x00`)

## 2. Repositorio de Catálogo bajo RLS

- [x] 2.1 Implementar `update_product` en `backend/app/modules/catalog/repository.py` consumiendo el modelo inmutable `Product` mediante `UPDATE ... WHERE id = :product_id AND business_id = :business_id RETURNING Product` dentro de `_transaction()` (`begin_nested()` savepoint), validando whitelist de columnas editables (`UPDATABLE_PRODUCT_FIELDS`) y retornando `Product | None`

## 3. Capa de Servicio de Catálogo

- [x] 3.1 Definir `ProductNotFoundError` e implementar `update_product` en `backend/app/modules/catalog/service.py` usando `payload.model_dump(exclude_unset=True)`, capturando `IntegrityError` (`sqlstate == "23505"` en `uq_products_business_id_code`) hacia `DuplicateProductCodeError`, lanzando `ProductNotFoundError` si el repositorio retorna `None` y devolviendo `ProductResponse` (`redact_cost=False`)

## 4. Router FastAPI y Sincronización Contractual OpenAPI

- [x] 4.1 Implementar la ruta `PATCH /api/v1/catalog/products/{product_id}` en `backend/app/modules/catalog/router.py` con `product_id: uuid.UUID`, `payload: ProductUpdate`, dependencias `require_owner` y `get_tenant_db`, mapeo de `ProductNotFoundError` a HTTP `404` (`PRODUCT_NOT_FOUND`), mapeo de `DuplicateProductCodeError` a HTTP `409` (`PRODUCT_CODE_ALREADY_EXISTS`) y respuestas OpenAPI `200`, `401`, `403`, `404`, `409` y `422` (`ErrorResponse`)
- [x] 4.2 Regenerar el contrato OpenAPI versionado en `docs/api/openapi.json` ejecutando `uv run --directory backend python -m app.scripts.export_openapi` y verificar sincronización con `uv run --directory backend python -m app.scripts.export_openapi --check`

## 5. Pruebas de Dominio, Integración RLS y Validación Determinista

- [x] 5.1 Ampliar `backend/tests/unit/test_catalog_schemas.py` con pruebas unitarias de `ProductUpdate` cubriendo actualización parcial (`exclude_unset=True`), `code: null` explícito vs `code` omitido, rechazo de `null` en `name`/`sale_price`/`cost_price`/`stock`, rechazo de `{}` vacío o solo campos no editables, validación estricta `Decimal` (`float`/`bool`/`NaN`/`Infinity`/escala `> 2`/overflow), `sale_price <= 0`, `cost_price < 0`, `stock < 0`, strings en blanco y bytes NUL
- [x] 5.2 Ampliar `backend/tests/integration/test_catalog_products.py` cubriendo todos los escenarios de `PATCH /api/v1/catalog/products/{product_id}`: edición parcial (`200 OK`) preservando campos omitidos (incluido stock negativo existente) y avanzando `updated_at` sin alterar `created_at`, edición completa incluyendo `code: null`, actualización conservando `code` propio o usando `code` de otro negocio (`200 OK`), colisión de `code` en mismo negocio (`409` con savepoint y sesión externa sana), rechazo `401`/`403` (`ONBOARDING_REQUIRED` y `FORBIDDEN` para `cashier`), `404 PRODUCT_NOT_FOUND` para producto inexistente o de otro tenant bajo `SET LOCAL ROLE app_api`, ignorado de `business_id` en body, `422` para UUID inválido o payload inválido y verificación de contrato en `/openapi.json` y `docs/api/openapi.json`
- [x] 5.3 Ejecutar validación completa de calidad y contrato (`cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy app && uv run pytest` y `uv run --directory backend python -m app.scripts.export_openapi --check`) confirmando 0 cambios en `backend/migrations/` y `backend/app/modules/catalog/models.py`
