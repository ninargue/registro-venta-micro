## 1. Piezas Core Compartidas y DTOs de Ventas (consumiendo `models.py` inmutables)

- [ ] 1.1 Promover `MAX_NUMERIC_12_2`, `DECIMAL_QUANTIZER`, `parse_strict_decimal` y `quantize_decimal` a `backend/app/core/schemas.py`, re-exportando `_parse_strict_decimal` en `backend/app/modules/catalog/schemas.py` para compatibilidad sin acoplamiento transversal
- [ ] 1.2 Definir esquemas Pydantic v2 en `backend/app/modules/sales/schemas.py` (`PaymentMethod`, `SaleItemCreate`, `SalePaymentCreate`, `SaleCreate`, `SaleItemResponse`, `SalePaymentResponse`, `SaleResponse`) con validación `Decimal` estricta (sin `float`/`bool`/`NaN`/`Infinity`, escala `<= 2`, tope `numeric(12,2)`), listas no vacías (`items`, `payments`), rechazo de `\x00`, serialización cuantizada a 2 decimales y omisión de `unit_cost` en la respuesta

## 2. Repositorios bajo RLS (Catálogo para Stock + Ventas Idempotente)

- [ ] 2.1 Ampliar `CatalogRepository` (`backend/app/modules/catalog/repository.py`) y `CatalogService` (`backend/app/modules/catalog/service.py`) consumiendo `Product` inmutable para proveer: `lock_products_for_sale` (`SELECT ... ORDER BY id ASC FOR UPDATE`), `deduct_stock_batch` (`UPDATE products SET stock = stock - :qty` en orden ascendente permitiendo saldo negativo) y `get_product_names_by_ids` compartiendo la misma `AsyncSession`
- [ ] 2.2 Implementar `SalesRepository` en `backend/app/modules/sales/repository.py` consumiendo `Sale`, `SaleItem` y `Payment` inmutables (`backend/app/modules/sales/models.py`): contexto `_transaction()` con `begin_nested()` savepoint, `get_sale_by_client_id` (cabecera + líneas y pagos ordenados determinísticamente por `(created_at, id)`), `try_insert_sale_header` (`INSERT ... ON CONFLICT (business_id, client_id) DO NOTHING RETURNING *`), `insert_sale_items` y `insert_payments`

## 3. Capa de Servicio Transaccional de Ventas

- [ ] 3.1 Implementar excepciones de dominio (`SaleProductNotFoundError`, `SaleProductInactiveError`, `SalePaymentMismatchError`, `SaleTotalInvalidError`) y `SalesService.create_sale` en `backend/app/modules/sales/service.py` colaborando con `SalesRepository` y `CatalogService` sobre la misma sesión RLS
- [ ] 3.2 Garantizar el flujo atómico e idempotente en `SalesService.create_sale`: lectura temprana por `(business_id, client_id)` (`200 OK`), bloqueo ordenado de productos, validación de faltantes/cross-tenant (`404`) e inactivos (`422`), recálculo de subtotales (`ROUND_HALF_UP` a `0.01`) y `total_amount` en `Decimal`, cuadratura exacta contra `SUM(payments.amount)` (`422`), inserción `ON CONFLICT DO NOTHING` previo a `deduct_stock_batch` (manejo de carrera concurrente sin doble descuento) y congelamiento de `unit_price`/`unit_cost`

## 4. Router FastAPI, Registro en App y Sincronización OpenAPI

- [ ] 4.1 Implementar `POST /api/v1/sales` en `backend/app/modules/sales/router.py` con `APIRouter(prefix="/sales", tags=["sales"])`, dependencias `get_current_tenant` y `get_tenant_db`, retorno `201 Created` en creación o `200 OK` en reintento idempotente, traducción de excepciones de dominio a `HTTPException` (`404`/`422` con `ErrorResponse`) y documentación explícita de `200`/`201`/`401`/`403`/`404`/`422`
- [ ] 4.2 Registrar `sales_router` en `backend/app/main.py` bajo `prefix="/api/v1"` y regenerar `docs/api/openapi.json` ejecutando `uv run --directory backend python -m app.scripts.export_openapi` sin modificar `backend/migrations/` ni archivos `models.py`

## 5. Pruebas de Dominio, Concurrencia, RLS y Validación Determinista

- [ ] 5.1 Implementar pruebas unitarias de esquemas y contrato en `backend/tests/unit/test_sales_schemas.py` cubriendo validación estricta `Decimal` (rechazo de `float`/`bool`/`NaN`/`Infinity`/escala `> 2`/overflow `numeric(12,2)`), listas vacías, métodos de pago inválidos, UUIDs inválidos, bytes `\x00` y serialización cuantizada sin `unit_cost`
- [ ] 5.2 Implementar pruebas de integración, concurrencia, rollback ACID e aislamiento RLS en `backend/tests/integration/test_sales.py` mapeando 1:1 todos los escenarios de `specs/sales-api/spec.md`: venta con pago simple y combinado (`201`), congelamiento de `unit_price`/`unit_cost` tras edición posterior de producto, redondeo fraccionario y líneas repetidas, stock negativo transitorio (`201`), rollback ACID ante falla mid-transacción, idempotencia secuencial (`200` incluso tras cambio de precio o desactivación) y concurrente (sin doble descuento), mismo `client_id` entre negocios distintos, `422 PAYMENT_TOTAL_MISMATCH`, `422 PRODUCT_INACTIVE`, `401`/`403` y autorización `owner`/`cashier`, `404 PRODUCT_NOT_FOUND` cross-tenant e ignorado de `business_id` en body, y verificación OpenAPI (`/openapi.json` y `export_openapi --check`)
- [ ] 5.3 Ejecutar validación completa (`cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy app && uv run pytest && uv run python -m app.scripts.export_openapi --check`) confirmando 0 cambios en `backend/migrations/` y modelos ORM
