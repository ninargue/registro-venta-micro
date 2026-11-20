<!--
Ticket: US-03-T07 | Issue: #47 (https://github.com/ninargue/registro-venta-micro/issues/47) | Capa: backend
Historia padre: US-03 (#45) | Dependencia BD cerrada: #46 (sales-schema-and-rls)
-->

## Why

Los micronegocios necesitan registrar ventas de mostrador combinando medios de pago, congelando precio y costo histórico, actualizando el stock de forma atómica sin rechazar ventas por saldo negativo y evitando duplicados ante reintentos de red. Habiéndose cerrado el esquema `sales`, `sale_items`, `payments`, las políticas RLS y los modelos ORM en `#46` (`sales-schema-and-rls`), el backend debe implementar el endpoint transaccional e idempotente `POST /api/v1/sales` consumiendo el modelo de base de datos existente sin alterarlo.

## What Changes

- **Registro transaccional de ventas (`POST /api/v1/sales`)**: Valida `client_id` (UUID), líneas (`product_id`, `quantity`) y desglose de `payments` (`payment_method`, `amount`) en `Decimal` estricto (prohibiendo `float`), recalcula subtotales y `total_amount` en servidor usando precios brutos vigentes de `products`, exige coincidencia exacta con la suma de pagos (`422 PAYMENT_TOTAL_MISMATCH`) y persiste cabecera, líneas congeladas (`unit_price`, `unit_cost`) y pagos en una única transacción ACID bajo RLS (`get_tenant_db`).
- **Descuento atómico de stock sin bloqueo negativo**: Bloquea filas de productos en orden determinista (`ORDER BY id FOR UPDATE`) y ejecuta `stock = stock - quantity` dentro de la misma transacción, permitiendo saldo negativo transitorio.
- **Idempotencia por negocio `(business_id, client_id)`**: Ante reintentos secuenciales o concurrentes con idéntico `client_id` (`ON CONFLICT DO NOTHING`), responde `200 OK` con el comprobante ya persistido sin duplicar registros ni re-descontar inventario.
- **Validaciones de dominio, seguridad y OpenAPI**: Rechaza productos inexistentes o de otro comercio con `404` (`PRODUCT_NOT_FOUND`), productos inactivos con `422` (`PRODUCT_INACTIVE`), errores de autenticación/onboarding con `401`/`403`, y actualiza `docs/api/openapi.json` conforme a ADR-0005.
- **Non-Goals**:
  - Modificar migraciones Alembic (`backend/migrations/`), políticas RLS o modelos ORM existentes (`products`, `sales`, `sale_items`, `payments` son inmutables tras `#42` y `#46`).
  - Implementar consulta/listado de ventas (`GET /api/v1/sales`), anulaciones, notas de crédito, impuestos, cajas (`cash_sessions`) o reportes diarios (`#50`).
  - Implementar componentes de interfaz o calculador de vuelto en frontend (`#48`).

## Capabilities

### New Capabilities
- `sales-api`: Endpoint `POST /api/v1/sales` transaccional e idempotente con cálculo estricto en `Decimal`, congelamiento de precio y costo unitario, deducción atómica de stock permitiendo saldo negativo, validación de cuadratura de pagos, manejo uniforme `ErrorResponse` y aislamiento multitenant bajo RLS.

### Modified Capabilities
*(Ninguna)*

## Impact

- **Backend (`backend/app`)**: Nuevo módulo `schemas.py`, `repository.py`, `service.py` y `router.py` en `backend/app/modules/sales/`, métodos de consulta/bloqueo y descuento atómico de stock en `backend/app/modules/catalog/`, promoción de helpers `Decimal` compartidos a `backend/app/core/schemas.py` y registro de `sales_router` en `backend/app/main.py`.
- **Base de Datos (Inmutable)**: Consume `backend/app/modules/sales/models.py`, `catalog/models.py` y la migración `d4e7f1a2b9c3` sin alteraciones (`No-DB-Diff`).
- **Contrato y Tests**: Actualización de `docs/api/openapi.json` y nuevas pruebas unitarias y de integración/RLS en `backend/tests/`.
- **Consumidores**: Desbloquea la pantalla de mostrador y carrito en frontend ([Issue #48](https://github.com/ninargue/registro-venta-micro/issues/48)).
