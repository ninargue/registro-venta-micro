# US-04: Reporte Diario de Ventas y Margen en Hora Local

**Épica:** E3-reportes  
**Estado:** Consolidada v0.2  
**GitHub Issue:** [#49](https://github.com/ninargue/registro-venta-micro/issues/49)  

---

## 1. Descripción
**Como** dueño del micronegocio,  
**quiero** consultar un reporte consolidado con las ventas del día, el desglose por medio de pago y el margen bruto estimado en la hora local de mi comercio,  
**para** conocer la recaudación real de la jornada sin cortes de día arbitrarios y sin necesidad de gestionar sesiones de caja.

---

## 2. Criterios de Aceptación (Given / When / Then)

### Escenario 1: Consulta del reporte diario del negocio en hora local
- **Dado** que soy el dueño autenticado en mi comercio,
- **cuando** accedo al panel de reportes para la fecha actual,
- **entonces** el sistema consulta las ventas del negocio resolviendo la fecha con la zona horaria del comercio (`(created_at AT TIME ZONE b.timezone)::date = :fecha`),
- **y** presenta en pantalla:
  - Total facturado bruto (sin impuestos).
  - Desglose por medio de pago: Total Efectivo, Total Tarjetas, Total Transferencias.
  - Cantidad total de transacciones completadas.
  - Costo total de mercadería vendida (sumando `quantity * unit_cost` congelado en cada línea de venta).
  - Margen bruto estimado (`Total Facturado - Costo Total`) y porcentaje de ganancia.

### Escenario 2: Día sin ventas
- **Dado** que un negocio no registró ventas en la fecha consultada,
- **cuando** se visualiza el reporte,
- **entonces** el sistema muestra totales en cero sin generar errores de división por cero ni valores nulos.

---

## 3. Reglas de Negocio
- Las fechas en base de datos residen en `timestamptz` (UTC) y se agrupan utilizando el `timezone` del comercio (`businesses.timezone`).
- Los cálculos monetarios se realizan en backend con precisión `Decimal`.
- El reporte es directo, desacoplado de sesiones o arqueos de caja.
