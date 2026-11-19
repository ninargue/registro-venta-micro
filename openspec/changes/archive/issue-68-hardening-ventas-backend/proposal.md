<!--
Ticket: Issue #68 (https://github.com/ninargue/registro-venta-micro/issues/68) | Capa: backend
Origen: Auditoría adversarial PR #64 (`docs/reviews/pr-64-review.md`) sobre Issue #47 (`sales-api`)
-->

## Why

La auditoría adversarial del PR #64 (`docs/reviews/pr-64-review.md`) identificó tres riesgos altos y cuatro brechas medias en `POST /api/v1/sales`: una carrera entre `FOR UPDATE` y la idempotencia concurrente ante edición del catálogo (H1), desbordamiento `numeric(12,2)` en `products.stock` no capturado que produce HTTP 500 (H2), devolución silenciosa de `200 OK` ante reutilización de `client_id` con distinto contenido (H3), deriva en `docs/api/openapi.json` (`type: "number"` frente al rechazo runtime de `float`, M1), falta de cobertura unitaria/concurrencia cruzada (M2–M3) y N round-trips sin filtro explícito `business_id` en `CatalogRepository` (M4). El Issue #68 endurece el servicio antes de conectar el mostrador y sincronización offline (#48).

## What Changes

- **H1 — Re-lookup idempotente post-lock**: Re-ejecutar `get_sale_by_client_id` inmediatamente después de `lock_products_for_sale` (dentro de la misma transacción) antes de validar `missing_ids`, `is_active` o cuadratura, evitando fallos `422` en reintentos concurrentes tras cambios de catálogo.
- **H2 — Guarda de overflow `numeric(12,2)` en stock**: Validar en `SalesService.create_sale` que `stock_deductions[pid] <= MAX_NUMERIC_12_2` y `(product.stock - total_qty) >= -MAX_NUMERIC_12_2`, devolviendo `422 VALIDATION_ERROR` en lugar de `500` (`SQLSTATE 22003`).
- **H3 — Detección de conflicto `409 SALE_ID_CONFLICT`**: En todos los puntos de detección de `client_id` existente (temprano, post-lock y post-`ON CONFLICT`), comparar `items` (`product_id`, `quantity` cuantizada) y `payments` (`payment_method`, `amount` cuantizada); responder `200 OK` si coinciden o `409 Conflict` (`ErrorResponse` con `code = "SALE_ID_CONFLICT"`) si difieren.
- **M1 — Contrato OpenAPI string-only**: Aplicar `WithJsonSchema` en `SaleItemCreate.quantity` y `SalePaymentCreate.amount` para publicar `type: "string"` (`format: "decimal"`) en `docs/api/openapi.json`, y documentar `409` en `POST /api/v1/sales`.
- **M2–M3 — Cobertura unitaria y concurrencia real**: Crear `backend/tests/unit/test_sales_schemas.py` para `.husky/pre-push` y añadir en `backend/tests/integration/test_sales_api.py` pruebas de concurrencia cruzada (`[P1, P2]` vs `[P2, P1]`), carrera H1, overflow H2, conflicto `409` H3 y límites (`max_length=500`, `20`, `unit_cost == 0.00`).
- **M4 — Defense-in-depth y batching en `CatalogRepository`**: Añadir filtro explícito `Product.business_id == business_id` en `lock_products_for_sale`, `deduct_stock_batch` y `get_product_names_by_ids`, y unificar `deduct_stock_batch` en un `UPDATE` masivo (`CASE WHEN`).

## Non-Goals

- **H4 — Reconciliación de precios en sincronización offline**: La política de precios cacheados vs precios actualizados para ventas del *outbox* offline queda explícitamente diferida al Issue #48 / diseño de sincronización offline.
- **Inmutabilidad del modelo de base de datos**: Prohibido modificar `backend/migrations/`, políticas RLS o modelos ORM (`Product`, `Sale`, `SaleItem`, `Payment`).
- Otros ítems de auditoría fuera del alcance aprobado (`M5` revalidación de membresía JWT en BD y `M6` columna `product_name` en `sale_items`).

## Capabilities

### New Capabilities
*(Ninguna)*

### Modified Capabilities
- `sales-api`: Endurecimiento de idempotencia concurrente post-lock (H1), rechazo `422` por desbordamiento `numeric(12,2)` en `stock` (H2), respuesta `409 SALE_ID_CONFLICT` por payload distinto con mismo `client_id` (H3) y contrato OpenAPI `type: "string"` + estado `409` (M1).

## Impact

- **Backend (`backend/app`)**: `backend/app/modules/sales/{schemas.py,service.py,router.py}` y `backend/app/modules/catalog/{repository.py,service.py}`.
- **Base de Datos (Inmutable)**: `No-DB-Diff` sobre revisión `d4e7f1a2b9c3`.
- **Contrato y Tests**: Regeneración de `docs/api/openapi.json`, creación de `backend/tests/unit/test_sales_schemas.py` y ampliación de `backend/tests/integration/test_sales_api.py`.
