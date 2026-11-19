<!--
Ticket: US-02-T03 | Issue: #42 (https://github.com/ninargue/registro-venta-micro/issues/42) | Capa: db
-->

## Why

El sistema `registro-venta-micro` ya cuenta con las tablas fundacionales multitenant `businesses` y `business_users` bajo Row-Level Security (RLS), pero aún carece de una entidad persistente para el catálogo e inventario de cada comercio. Para habilitar la carga/edición de productos (US-02) y el descuento atómico de stock en ventas (US-03), se requiere crear la tabla `products` con precisión decimal exacta (`numeric(12,2)`), baja lógica y aislamiento estricto por `business_id` en PostgreSQL.

## What Changes

- **Tabla `products`**: Nueva entidad operativa vinculada a `businesses(id)` con `ON DELETE CASCADE`, columnas `id` (`uuid`), `business_id` (`uuid` NOT NULL), `code` (`varchar(50)` nullable, único por negocio cuando no es nulo), `name` (`varchar(150)` NOT NULL), `sale_price` (`numeric(12,2)` > 0), `cost_price` (`numeric(12,2)` >= 0), `stock` (`numeric(12,2)` NOT NULL DEFAULT 0), `is_active` (`boolean` NOT NULL DEFAULT true para baja lógica que preserva integridad con histórico de ventas), `created_at` y `updated_at` (`timestamptz` con trigger `BEFORE UPDATE`).
- **Precisión financiera y regla de stock**: Uso estricto de `numeric(12,2)` sin `float`. Siguiendo el PRD v0.2 (§1.2, §3 US-03), `stock` no impone `CHECK (stock >= 0)` en base de datos para permitir saldo negativo transitorio ante ventas en mostrador (el stock inicial `>= 0` en alta se valida en la capa API de `#43`).
- **Seguridad RLS y DCL**: Activación de `ENABLE` y `FORCE ROW LEVEL SECURITY` con políticas granulares (`SELECT`, `INSERT`, `UPDATE` con `USING`+`WITH CHECK`, `DELETE`) filtradas por `app.current_business_id`; `REVOKE ALL` a `PUBLIC`, `anon`, `authenticated`; y `GRANT SELECT, INSERT, UPDATE, DELETE` exclusivo para `app_api` (heredado por `app_runtime`).
- **Sincronización ORM y Migración Alembic**: Nueva migración incremental reversible sobre `f8b2c1a94d07`, modelo SQLAlchemy `Product` en `backend/app/modules/catalog/models.py` registrado en `backend/app/db/base.py` (requerido por `alembic check` en CI) y suite DB-TDD en `backend/tests/integration/test_db_products.py`.

## Non-goals

- Endpoints REST de catálogo (`GET`/`POST` `/api/v1/catalog/products`), esquemas Pydantic o servicios FastAPI (corresponden a Issue `#43` / `TICKET-04`).
- Vistas PWA de catálogo (Issue `#44` / `TICKET-05`).
- Tablas de ventas, líneas de venta, pagos o movimientos de kardex (`sales`, `sale_items`, `payments`, Issue `#46` / `TICKET-06`).
- Categorías, múltiples códigos de barras, unidades fraccionarias `numeric(12,3)` o extensión `pg_trgm` (fuera del alcance acotado del MVP).

## Capabilities

### New Capabilities
- `products-schema-and-rls`: Esquema relacional de productos por comercio, restricciones de integridad monetaria/stock (`numeric(12,2)`), unicidad parcial de código, baja lógica y aislamiento RLS/DCL bajo `app_api`/`app_runtime`.

### Modified Capabilities
*(Ninguna)*

## Impact

- **Base de Datos y Migraciones**: Nueva revisión Alembic en `backend/migrations/versions/` (descendiente de `f8b2c1a94d07`), sin alterar migraciones existentes.
- **ORM Backend**: Nuevo archivo `backend/app/modules/catalog/models.py` y registro en `backend/app/db/base.py`.
- **Tests**: Nueva suite de integración DB-TDD y aislamiento RLS en `backend/tests/integration/test_db_products.py`.
- **Compatibilidad y Desbloqueo**: Aditivo y 100% compatible con `businesses`; desbloquea `#43` (API catálogo) y `#46` (esquema ventas).
