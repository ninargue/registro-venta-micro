## 1. Esquemas DTOs y Contrato OpenAPI (M1)

- [ ] 1.1 Aplicar `WithJsonSchema` (ej. `DecimalInput = Annotated[Decimal, WithJsonSchema({"type": "string", "format": "decimal", "pattern": r"^\d{1,10}(\.\d{1,2})?$"})]`) en `SaleItemCreate.quantity` y `SalePaymentCreate.amount` dentro de `backend/app/modules/sales/schemas.py`, conservando los metadatos de `Field(...)` y el rechazo runtime de `float`/`bool` mediante `parse_strict_decimal`.

## 2. Repositorios y Servicio de Catálogo bajo RLS (M4)

- [ ] 2.1 Añadir el parámetro obligatorio `business_id: uuid.UUID` y el predicado explícito `Product.business_id == business_id` en `lock_products_for_sale`, `deduct_stock_batch` y `get_product_names_by_ids` dentro de `backend/app/modules/catalog/repository.py`, optimizando `deduct_stock_batch` a un único `UPDATE` masivo con `sqlalchemy.case` y `literal(..., type_=Numeric(12, 2))` en lugar de N round-trips.
- [ ] 2.2 Actualizar `CatalogService` en `backend/app/modules/catalog/service.py` para exigir y propagar `business_id: uuid.UUID` en `lock_products_for_sale`, `deduct_stock_batch` y `get_product_names_by_ids`.

## 3. Capa de Servicio Transaccional de Ventas (H1, H2, H3, M4)

- [ ] 3.1 Incorporar las excepciones de dominio `SaleStockOverflowError` (H2) y `SaleIdConflictError` (H3, con `client_id: uuid.UUID`), junto al helper `_assert_idempotent_payload_matches` en `backend/app/modules/sales/service.py` comparando multiconjuntos ordenados de `(product_id, quantize_decimal(quantity))` y `(payment_method, quantize_decimal(amount))`.
- [ ] 3.2 Endurecer `SalesService.create_sale` en `backend/app/modules/sales/service.py` para: (a) pasar `business_id` en todas las invocaciones a `CatalogService` (M4), (b) re-ejecutar `get_sale_by_client_id` inmediatamente después de `lock_products_for_sale` antes de validar faltantes, `is_active` o cuadratura (H1), (c) validar `stock_deductions[pid] <= MAX_NUMERIC_12_2` y `(quantize_decimal(product.stock) - total_qty) >= -MAX_NUMERIC_12_2` antes de `PAYMENT_TOTAL_MISMATCH` lanzando `SaleStockOverflowError` (H2), y (d) ejecutar `_assert_idempotent_payload_matches` en los tres puntos de detección de `client_id` existente (temprano, post-lock y post-`ON CONFLICT`) (H3).

## 4. Router FastAPI y Sincronización OpenAPI (H2, H3, M1)

- [ ] 4.1 Actualizar `POST /api/v1/sales` en `backend/app/modules/sales/router.py` para documentar `409: {"model": ErrorResponse}`, mapear `SaleIdConflictError` a HTTP `409 Conflict` (`ErrorResponse(code="SALE_ID_CONFLICT", details={"client_id": ...})`) y mapear `SaleStockOverflowError` a HTTP `422 Unprocessable Content` (`ErrorResponse(code="VALIDATION_ERROR", details=None)`).
- [ ] 4.2 Regenerar `docs/api/openapi.json` ejecutando `uv run --directory backend python -m app.scripts.export_openapi`, verificando `type: "string"` en `SaleItemCreate.quantity` y `SalePaymentCreate.amount` y respuesta `409` en `/api/v1/sales`, sin alterar `backend/migrations/` ni modelos ORM.

## 5. Pruebas Unitarias, Integración, Concurrencia y Validación Final (M2, M3)

- [ ] 5.1 Crear `backend/tests/unit/test_sales_schemas.py` cubriendo validación estricta `Decimal`, rechazo de `float`/`bool`/`NaN`/`Infinity`/escala `> 2`/overflow, límites `max_length=500`/`20`, `payment_method`, `\x00`, UUIDs inválidos, `extra="ignore"` de `business_id`, serialización cuantizada sin `unit_cost`, contrato OpenAPI `type: "string"` en `SaleItemCreate.quantity` y `SalePaymentCreate.amount`, y reglas puras de `SalesService` (cálculo `ROUND_HALF_UP`, equivalencia/conflicto H3, precedencia post-lock H1 y cotas H2) para que `.husky/pre-push` ejecute tests de `sales`.
- [ ] 5.2 Ampliar `backend/tests/integration/test_sales_api.py` con pruebas reales contra PostgreSQL cubriendo: concurrencia cruzada (`asyncio.gather` con `[P1, P2]` vs `[P2, P1]` sin deadlocks ni *lost updates*), carrera H1 (edición/desactivación de catálogo entre lookup temprano y `FOR UPDATE` devolviendo `200 OK`), overflow `numeric(12,2)` de stock (`422 VALIDATION_ERROR` y frontera `-9999999999.99` `201`), conflicto `409 SALE_ID_CONFLICT` (temprano, post-lock y `ON CONFLICT` + reintento multi-línea `200 OK`), límites `500`/`501` ítems, `20`/`21` pagos, `unit_cost == 0.00`, verificación SQL de `UPDATE` único con `CASE WHEN` y filtro `business_id` (M4), y aserción OpenAPI (`409` + `type: "string"`).
- [ ] 5.3 Ejecutar validación completa (`cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy app && uv run pytest && uv run python -m app.scripts.export_openapi --check`) confirmando 0 cambios en `backend/migrations/` y modelos ORM.
