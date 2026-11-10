# Tickets Técnicos — US-04: Reporte Diario de Ventas y Margen en Hora Local

---

### TICKET-09: Endpoint de consolidado diario de ventas y margen con zona horaria
- **Alcance / Capa:** Backend (`backend/app/modules/reports`)
- **Talla:** `M` | **Riesgo:** Bajo
- **Dependencias:** `TICKET-06`
- **Descripción:** Implementar endpoint `GET /api/v1/reports/daily` que agrupe las ventas utilizando la zona horaria del comercio (`(created_at AT TIME ZONE b.timezone)::date = :fecha`) para el `business_id` autenticado, calculando total facturado, desglose por medio de pago, costo total acumulado y margen bruto estimado.
- **Definición de Terminado (DoD):**
  - [ ] Consulta SQL optimizada agrupando por fecha local del comercio.
  - [ ] Cálculo de costo de mercadería vendida sumando `quantity * unit_cost` de `sale_items`.
  - [ ] Cálculo de margen bruto en `Decimal`: `total_ventas - total_costos` y rentabilidad protegida contra división por cero.
  - [ ] Tests de integración para días con ventas y días sin ventas (valores en cero sin nulos).

---

### TICKET-10: Vista de reporte diario y KPIs de ganancia en frontend
- **Alcance / Capa:** Frontend (`frontend/src/app`)
- **Talla:** `S` | **Riesgo:** Bajo
- **Dependencias:** `TICKET-09`
- **Descripción:** Crear la pantalla de reportes para el dueño en la PWA con tarjetas de métricas del día (Ventas Totales, Margen Bruto, Tickets) y gráfico o tabla simple de medios de pago.
- **Definición de Terminado (DoD):**
  - [ ] Tarjetas con KPIs destacados y formato de moneda local.
  - [ ] Desglose por medio de pago (Efectivo, Tarjeta, Transferencia).
  - [ ] Manejo de estados de carga y pantalla vacía para días sin ventas.
