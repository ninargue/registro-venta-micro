<!--
Ticket: US-02-T04b | Issue: #67 (https://github.com/ninargue/registro-venta-micro/issues/67) | Capa: backend
Historia padre: US-02 (#41) | Dependencia cerrada: #43 (US-02-T04) | Bloquea: #44 (US-02-T05)
-->

## Why

Los dueños de micronegocios necesitan corregir o actualizar atributos de productos existentes en su catálogo (código/SKU, nombre, precio de venta, costo de referencia y stock) sin recrear registros ni alterar los precios congelados en ventas históricas (US-02, Escenario 3). Habiéndose completado el listado y alta (`GET`/`POST /api/v1/catalog/products`) en `#43`, falta exponer el endpoint de edición parcial requerido por la interfaz de catálogo (`#44`).

## What Changes

- **Edición parcial de productos (`PATCH /api/v1/catalog/products/{product_id}`)**: Permite al dueño autenticado (`role == "owner"`) modificar parcialmente cualquiera de los campos editables (`code`, `name`, `sale_price`, `cost_price`, `stock`) de un producto existente de su comercio, devolviendo HTTP `200 OK` con `ProductResponse`.
- **Validación estricta de entrada (`ProductUpdate`)**: Valida montos y stock en `Decimal` exacto (`numeric(12,2)`, prohibiendo `float`/`bool`/`NaN`/`Infinity` y más de 2 decimales), exigiendo `sale_price > 0`, `cost_price >= 0` y `stock >= 0` cuando se informan, permitiendo limpiar `code` a `null` de forma explícita, y rechazando payloads vacíos (`{}`) o `null` en campos obligatorios con HTTP `422`.
- **Seguridad RLS, unicidad y errores uniformes**: Restringe la edición a `owner` (`403 FORBIDDEN` para `cashier`), devuelve `404` (`PRODUCT_NOT_FOUND`) ante IDs inexistentes o pertenecientes a otro tenant (aislamiento vía `get_tenant_db` / RLS), mapea colisiones de `code` en el mismo comercio (`23505`) a `409 Conflict` (`PRODUCT_CODE_ALREADY_EXISTS`) mediante savepoint, y usa `ErrorResponse` uniforme.
- **Sincronización contractual OpenAPI**: Documenta `PATCH /api/v1/catalog/products/{product_id}` y `ProductUpdate` en OpenAPI y regenera `docs/api/openapi.json` mediante `app.scripts.export_openapi` (ADR-0005).
- **Non-goals**:
  - Modificar migraciones Alembic (`backend/migrations/`), políticas RLS o `backend/app/modules/catalog/models.py` (inmutables tras `#42`).
  - Implementar lectura unitaria (`GET /api/v1/catalog/products/{id}`), baja lógica (`DELETE` / edición de `is_active`) o reemplazo total (`PUT`).
  - Implementar la interfaz React/PWA de edición (`#44`) ni ajustes de inventario por ventas (`#46`/`#47`).

## Capabilities

### New Capabilities
*(Ninguna)*

### Modified Capabilities
- `catalog-products-api`: Agrega la operación `PATCH /api/v1/catalog/products/{product_id}`, el esquema `ProductUpdate`, las reglas de aislamiento `404` entre tenants, manejo de conflicto `409` al actualizar `code` y la actualización de `docs/api/openapi.json`.

## Impact

- **Backend (`backend/app/modules/catalog/`)**: Extensión de `schemas.py`, `repository.py`, `service.py` y `router.py` manteniendo compatibilidad 100% hacia atrás con `GET` y `POST /api/v1/catalog/products` y los esquemas existentes (`ProductCreate`, `ProductResponse`, `ProductListResponse`).
- **Contrato API (`docs/api/openapi.json`)**: Regeneración determinista vía `uv run --directory backend python -m app.scripts.export_openapi` sin romper consumidores actuales.
- **Tests (`backend/tests/`)**: Nuevos casos unitarios en `tests/unit/test_catalog_schemas.py` y de integración/RLS en `tests/integration/test_catalog_products.py`.
- **Consumidores**: Desbloquea el formulario de edición de productos en frontend ([Issue #44](https://github.com/ninargue/registro-venta-micro/issues/44)).
