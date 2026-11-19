<!--
Ticket: US-04-T09 | Issue: #50 (https://github.com/ninargue/registro-venta-micro/issues/50) | Capa: backend
Historia padre: US-04 (#49) | Dependencia BD cerrada: TICKET-06 (#46, sales-schema-and-rls)
-->

## Why

Los dueños de micronegocios necesitan conocer al cierre de la jornada cuánto vendieron, cómo se distribuyó la recaudación por medio de pago y cuál fue su margen bruto real sin cortes de día desplazados por UTC ni arqueos de caja. Con el esquema de ventas (`sales`, `sale_items`, `payments`) y la zona horaria por comercio (`businesses.timezone`) ya consolidados en base de datos, corresponde exponer el endpoint consolidado diario en la capa backend.

## What Changes

- **Endpoint de consolidado diario (`GET /api/v1/reports/daily`)**: Agrega las ventas del `business_id` autenticado agrupando por su fecha local (`(created_at AT TIME ZONE b.timezone)::date = :fecha`), aceptando parámetro opcional `date` (`YYYY-MM-DD`, por defecto fecha actual en la zona horaria del comercio).
- **Métricas y desglose en precisión `Decimal`**: Calcula `total_sales`, `transactions_count`, `payment_breakdown` (`cash`, `card`, `transfer`), `total_cost` (`SUM(quantity * unit_cost)` desde `sale_items`), `gross_margin` (`total_sales - total_cost`) y `margin_percentage` protegido contra división por cero. Días sin ventas devuelven valores en cero (`"0.00"` / `0`) sin nulos.
- **Seguridad, RLS y OpenAPI**: Restringe el acceso al rol `owner` bajo contexto transaccional RLS (`get_tenant_db`), responde errores uniformes (`ErrorResponse`) y actualiza la documentación OpenAPI (`code-first`).
- **Non-goals**:
  - Alterar migraciones Alembic (`backend/migrations/`), políticas RLS o modelos ORM existentes (`businesses`, `sales`, `sale_items`, `payments`), los cuales son inmutables (`No-DB-Diff`).
  - Implementar reportes por rango de fechas, ranking por producto, cierres de caja (`cash_sessions`) o asistente de IA.
  - Desarrollar la vista de reportes en la PWA frontend (cubierta por `TICKET-10` / Issue `#51`).

## Capabilities

### New Capabilities
- `daily-sales-report-api`: Endpoint REST `GET /api/v1/reports/daily` con agrupación por zona horaria del comercio, agregación sin fan-out de ventas/costos/pagos en `Decimal`, protección ante división por cero, autorización `owner` y aislamiento multitenant bajo RLS.

### Modified Capabilities
*(Ninguna)*

## Impact

- **Backend (`backend/app`)**: Nuevo módulo en capas (`schemas.py`, `repository.py`, `service.py`, `router.py`) en `backend/app/modules/reports/` y registro en `backend/app/main.py` bajo `/api/v1`.
- **Contrato OpenAPI (`docs/api/openapi.json`)**: Se regenerará estáticamente tras implementar la ruta y esquemas para mantener paridad en CI.
- **Base de Datos (Inmutable)**: Solo lectura bajo RLS sobre `businesses`, `sales`, `sale_items` y `payments` (`No-DB-Diff`).
- **Tests (`backend/tests`)**: Nueva suite unitaria de esquemas/cálculos y suite de integración HTTP + RLS (días con ventas, frontera de zona horaria, días sin ventas, precisión `Decimal`, RBAC y aislamiento multitenant).
- **Consumidores**: Habilita la vista de KPIs diarios en frontend (`TICKET-10` / [Issue #51](https://github.com/ninargue/registro-venta-micro/issues/51)) sin romper rutas ni contratos existentes de `auth`, `catalog` o `health`.
