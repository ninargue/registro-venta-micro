<!--
Ticket: US-03-T06 | Issue: #46 (https://github.com/ninargue/registro-venta-micro/issues/46) | Capa: db
-->

## Why

El esquema ya cuenta con `businesses`, `business_users` y `products` bajo Row-Level Security (RLS), pero aún carece de tablas transaccionales para persistir ventas, ítems vendidos y pagos multimedio. Para habilitar el servicio transaccional de ventas con idempotencia (`TICKET-07`) y el reporte diario de ventas y margen (`TICKET-09`), se requiere crear `sales`, `sale_items` y `payments` en PostgreSQL 17 con aislamiento estricto por negocio.

## What Changes

- **Tabla `sales`**: Cabecera de venta por negocio (`id` UUID PK, `business_id` FK a `businesses(id)` ON DELETE CASCADE, `client_id` UUID con unicidad compuesta `(business_id, client_id)` para idempotencia, `total_amount` en `numeric(12,2) > 0`, `created_at` `timestamptz` y clave única `(business_id, id)` para FKs compuestas).
- **Tabla `sale_items`**: Detalle de productos vendidos con FKs compuestas `(business_id, sale_id)` (`ON DELETE CASCADE`) y `(business_id, product_id)` (`ON DELETE RESTRICT`), `quantity` (`numeric(12,2) > 0`), y snapshot congelado de `unit_price` (`numeric(12,2) > 0`) y `unit_cost` (`numeric(12,2) >= 0`).
- **Tabla `payments`**: Desglose de medios de pago por venta con FK compuesta `(business_id, sale_id)` (`ON DELETE CASCADE`), `payment_method` (`'cash' | 'card' | 'transfer'`) y `amount` (`numeric(12,2) > 0`).
- **Seguridad RLS y DCL**: `ENABLE` + `FORCE ROW LEVEL SECURITY` en las tres tablas, políticas granulares (`SELECT`, `INSERT`, `UPDATE` con `USING`+`WITH CHECK`, `DELETE`) filtradas por `app.current_business_id`, `REVOKE ALL` a `PUBLIC`, `anon`, `authenticated` y `GRANT SELECT, INSERT, UPDATE, DELETE` exclusivo para `app_api` (heredado por `app_runtime`).
- **Sincronización ORM y Migración Alembic**: Nueva migración incremental reversible sobre `a3f9d2e1b4c8`, modelos SQLAlchemy (`Sale`, `SaleItem`, `Payment`) en `backend/app/modules/sales/models.py` registrados en `backend/app/db/base.py`, y suite DB-TDD en `backend/tests/integration/test_db_sales.py`.

## Non-goals

- Endpoints REST (`POST /api/v1/sales`, `GET /api/v1/reports/daily`), descuento atómico de stock o validación cruzada de suma de pagos contra `total_amount` (corresponden a `#47` / `TICKET-07` y `#50` / `TICKET-09`).
- Pantallas de mostrador, carrito o reportes en PWA (`#48` / `TICKET-08` y `#51` / `TICKET-10`).
- Tablas descartadas del MVP acotado (`cash_sessions`, `stock_movements`, anulaciones/notas de crédito, descuentos o impuestos).

## Capabilities

### New Capabilities
- `sales-schema-and-rls`: Esquema relacional de ventas (`sales`), ítems con precio/costo congelados (`sale_items`) y pagos multimedio (`payments`), idempotencia por `(business_id, client_id)`, integridad referencial compuesta y aislamiento RLS/DCL bajo `app_api`/`app_runtime`.

### Modified Capabilities
*(Ninguna)*

## Impact

- **Base de Datos y Migraciones**: Nueva revisión Alembic en `backend/migrations/versions/` descendiente de `a3f9d2e1b4c8`, sin modificar migraciones existentes.
- **ORM Backend**: Nuevo archivo `backend/app/modules/sales/models.py` registrado en `backend/app/db/base.py` (para `alembic check` en CI).
- **Tests y Documentación**: Nueva suite en `backend/tests/integration/test_db_sales.py` y actualización de `docs/04-modelo-de-datos/erd.md`.
- **Compatibilidad**: Cambio aditivo 100% compatible con `businesses` y `products` (usa `uq_products_business_id_id`); desbloquea `#47` y `#50`.
