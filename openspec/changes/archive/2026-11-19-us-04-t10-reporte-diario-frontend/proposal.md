<!--
Ticket: US-04-T10 | Issue: #51 (https://github.com/ninargue/registro-venta-micro/issues/51) | Capa: frontend
Historia padre: US-04 (#49, https://github.com/ninargue/registro-venta-micro/issues/49) | Dependencia Backend cerrada: TICKET-09 (#50, daily-sales-report-api)
-->

## Why

Los dueños de micronegocios necesitan consultar en la PWA el consolidado diario de ventas, el costo de mercadería vendida, el margen bruto con su porcentaje de rentabilidad y el desglose por medio de pago en la hora local de su comercio sin cortes desplazados por UTC ni sesiones de caja. Con el endpoint `GET /api/v1/reports/daily` y su contrato OpenAPI (`DailyReportResponse`, `PaymentMethodBreakdown`, `ErrorResponse`) consolidados en `TICKET-09`, corresponde implementar la vista de reporte diario en la capa frontend.

## What Changes

- **Ruta y vista de reporte diario (`/reports/daily`)**: Registra la pantalla de reporte diario en `frontend/src/app/router.tsx` (preservando intacta la ruta raíz `/` y su smoke test existente) con selector de fecha opcional (`YYYY-MM-DD`, por defecto resuelta por el backend en la zona horaria del comercio al omitir el parámetro inicial) y visualización de la fecha y `timezone` IANA aplicadas.
- **Tarjetas de KPIs y formato monetario/porcentual exacto**: Presenta tarjetas accesibles para Ventas Totales (`total_sales`), Margen Bruto (`gross_margin` y `margin_percentage`), Costo Total (`total_cost`) y Cantidad de Tickets (`transactions_count`), formateando importes a partir de las cadenas de dos decimales del contrato sin deriva de punto flotante.
- **Desglose por medio de pago**: Muestra tabla/lista semántica de `payment_breakdown` para Efectivo (`cash`), Tarjeta (`card`) y Transferencia (`transfer`) con sus montos y proporción respecto al total facturado (0% cuando `total_sales` es `"0.00"`).
- **Estados de pantalla observables (`loading`, `empty`, `ready`, `error`)**: Maneja estado de carga inicial/recarga, estado de día sin ventas (`transactions_count === 0` mostrando totales en cero sin nulos ni errores de división por cero y mensaje informativo de jornada sin ventas), estado con ventas (`ready`) y estado de error HTTP (`401`, `403`, `404`, `422`, `5xx`/red) con opción de reintento.
- **Non-goals**:
  - Modificar `docs/api/openapi.json`, migraciones en `backend/migrations/` o código en `backend/app/` (contrato `contract-first` e infraestructura backend 100% inmutables).
  - Implementar reportes por rango de fechas, gráficos complejos con librerías externas de charting, exportación CSV/PDF, cierres/arqueos de caja o asistente de IA.
  - Almacenar o calcular el reporte diario en IndexedDB/Dexie o Service Worker offline: el reporte diario es una consulta analítica online en tiempo real contra `GET /api/v1/reports/daily` bajo RLS.

## Capabilities

### New Capabilities
- `daily-sales-report-ui`: Vista de reporte diario en la PWA (`/reports/daily`) con tarjetas de KPIs (Ventas Totales, Margen Bruto y rentabilidad, Costo Total, Tickets), desglose por medio de pago (Efectivo, Tarjeta, Transferencia), filtro por fecha local (`YYYY-MM-DD`) y manejo accesible de estados `loading`, `empty` (día sin ventas con totales en cero), `ready` y `error`.

### Modified Capabilities
*(Ninguna)*

## Impact

- **Frontend (`frontend/src/`)**: Nuevo módulo `frontend/src/features/reports/` (tipos/cliente API alineados con `docs/api/openapi.json`, hook TanStack Query `useDailyReport`, componentes presentacionales puros de KPIs, desglose de pagos y vista `/reports/daily`) y registro de ruta en `frontend/src/app/router.tsx`.
- **Tests (`frontend/src/`)**: Nuevos handlers MSW para `GET /api/v1/reports/daily` y suites unitarias/integración *Design-Blind* en Vitest + Testing Library para componentes, estados (`loading`, `empty`, `ready`, `error`), selector de fecha y cliente/hook.
- **Impacto Offline / PWA**: `pwa_mode: none` y `offline_store: none` en este cambio; no se agregan tablas en Dexie ni interceptores de caché en Service Worker para `/api/v1/reports/daily`, evitando mostrar cierres contables obsoletos.
- **Dependencias y Bundle**: Cero dependencias nuevas en `package.json`; reutiliza React 19, React Router 8, TanStack Query v5 y tokens CSS en `frontend/src/index.css` (`ADR-0007`), manteniéndose dentro del presupuesto de bundle (`<= 250 KB`).
