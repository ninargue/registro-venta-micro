<!--
Ticket: US-02-T04 | Issue: #43 (https://github.com/ninargue/registro-venta-micro/issues/43) | Capa: backend
Historia padre: US-02 (#41) | Dependencia BD cerrada: #42 (products-schema-and-rls)
-->

## Why

Los micronegocios necesitan consultar y registrar productos en su catálogo con precio de venta bruto, costo de referencia y stock inicial para operar el mostrador y controlar márgenes. Habiéndose completado el esquema `products`, las políticas RLS y el modelo ORM `Product` en `#42` (`products-schema-and-rls`), la capa backend debe exponer la API REST de catálogo consumiendo dicho contrato de base de datos sin modificarlo.

## What Changes

- **Listado y búsqueda de catálogo (`GET /api/v1/catalog/products`)**: Expone el catálogo del comercio autenticado bajo RLS (`get_tenant_db`), ordenado determinísticamente por `name ASC, id ASC`, con filtro opcional por texto (`q`) insensible a mayúsculas sobre `name` o `code` (escapando comodines SQL `%`, `_`, `\`), filtro `include_inactive` (por defecto `false`) y paginación acotada (`limit`, `offset`) devolviendo `items`, `total`, `limit` y `offset`.
- **Alta de productos (`POST /api/v1/catalog/products`)**: Permite al dueño (`role == "owner"`) crear ítems en `products` derivando `business_id` exclusivamente del JWT, validando precisión exacta `Decimal` (`numeric(12,2)`, prohibiendo `float`), `sale_price > 0`, `cost_price >= 0` y `stock >= 0`, y traduciendo conflictos de código duplicado por negocio (`uq_products_business_id_code`, SQLSTATE `23505`) a `409 Conflict` (`ErrorResponse`).
- **Seguridad, errores y OpenAPI**: Propaga contexto transaccional RLS (`app_api`, `app.current_user_id`, `app.current_business_id`), exige `role == "owner"` en alta (`403 FORBIDDEN` para `cashier`) y redacta `cost_price: null` si un `cashier` consulta el listado, documentando todas las rutas y esquemas en OpenAPI `/openapi.json`.
- **Non-goals**:
  - Alterar migraciones Alembic (`backend/migrations/`), políticas RLS o el modelo `Product` en `backend/app/modules/catalog/models.py` (inmutables tras `#42`).
  - Implementar endpoints de edición (`PATCH`/`PUT`), baja lógica (`DELETE`) o detalle unitario (`GET /products/{id}`).
  - Crear tablas o flujos de ventas/kardex (`#46`/`#47`) ni vistas de frontend (`#44`).

## Capabilities

### New Capabilities
- `catalog-products-api`: Endpoints REST `GET /api/v1/catalog/products` y `POST /api/v1/catalog/products` con validación estricta `Decimal` (sin `float`), búsqueda segura por nombre/código, manejo de unicidad `409`, autorización por rol y aislamiento multitenant bajo RLS.

### Modified Capabilities
*(Ninguna)*

## Impact

- **Backend (`backend/app`)**: Nuevos módulos `schemas.py`, `repository.py`, `service.py` y `router.py` en `backend/app/modules/catalog/`, registro en `backend/app/main.py` bajo `/api/v1`, esquema compartido `ErrorResponse` y guardia `require_owner` en `backend/app/core/`.
- **Base de Datos (Inmutable)**: Consume `backend/app/modules/catalog/models.py` y la migración `a3f9d2e1b4c8` sin alteraciones (`No-DB-Diff`).
- **Tests (`backend/tests`)**: Nueva suite unitaria de esquemas (`tests/unit/test_catalog_schemas.py`) y de integración/aislamiento RLS (`tests/integration/test_catalog_products.py`).
- **Consumidores**: Desbloquea la vista de administración y selector de catálogo en frontend ([Issue #44](https://github.com/ninargue/registro-venta-micro/issues/44)).
