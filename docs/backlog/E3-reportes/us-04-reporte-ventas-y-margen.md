# US-04: Reporte Diario de Ventas y Margen Estimado

**Épica:** E3-reportes  
**Estado:** Lista para refinamiento técnico  

---

## 1. Descripción
**Como** dueño del micronegocio,  
**quiero** consultar un reporte consolidado con las ventas del día, el desglose por medio de pago y el margen bruto estimado,  
**para** conocer la recaudación real del negocio y el beneficio generado al finalizar la jornada de forma directa y sin necesidad de gestionar sesiones de caja.

---

## 2. Criterios de Aceptación (Given / When / Then)

### Escenario 1: Consulta del reporte diario del negocio
- **Dado** que soy el dueño autenticado en mi negocio,
- **cuando** accedo al panel de reportes para el día de hoy,
- **entonces** el sistema consulta las ventas del negocio correspondientes a la fecha (filtradas por RLS),
- **y** presenta en pantalla:
  - Total facturado bruto.
  - Desglose de ingresos por medio de pago: Total Efectivo, Total Tarjetas, Total Transferencias.
  - Cantidad total de transacciones / tickets emitidos.
  - Costo total de mercadería vendida (sumando `quantity * unit_cost` congelado en cada línea de venta).
  - Margen bruto estimado (`Total Facturado - Costo Total`) y porcentaje de margen sobre venta.

### Escenario 2: Día sin ventas
- **Dado** que un negocio no registró ventas en la fecha consultada,
- **cuando** se visualiza el reporte,
- **entonces** el sistema muestra totales en cero sin generar errores ni valores nulos.

---

## 3. Reglas de Negocio
- El reporte solo puede ser consultado por usuarios con rol de dueño o administrador del negocio.
- El cálculo de costo de venta utiliza obligatoriamente el `unit_cost` congelado en `sale_items`, protegiendo la métrica contra variaciones posteriores en el catálogo de productos.
- Todos los cálculos se realizan en backend con precisión `Decimal`.
- El reporte opera de forma desacoplada de cualquier concepto de caja o turno.

---

## 4. Fuera de Alcance de esta Historia
- Apertura o cierre de caja y arqueos.
- Asistente de IA en lenguaje natural para consultas.
- Exportación a PDF o Excel en este lote.
