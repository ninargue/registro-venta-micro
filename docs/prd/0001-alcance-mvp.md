# Alcance — registro-venta-micro (mvp)

> Fecha: 2026-11-09  
> Basado en: Revisión de la Primera Entrega y refinamiento de alcance  
> Estado: Consolidado con ajustes del usuario (sin sesiones de caja)

---

## 1. Problema

Los micronegocios (kioscos, ferreterías de barrio, almacenes y puestos de mercado) necesitan agilidad y control básico:
1. **Cobro ágil y ordenado:** Poder registrar ventas en pocos toques desde el celular admitiendo múltiples medios de pago combinados (efectivo, tarjeta, transferencias/billeteras virtuales).
2. **Margen de ganancia visible:** Conocer al final del día cuánto se vendió y cuál fue la ganancia bruta estimada sin cálculos manuales complejos.

Para este primer lote, el alcance se acota al núcleo transaccional más limpio posible: se prescinde de aperturas/cierres de turnos de caja y del descuento de inventario en tiempo real.

---

## 2. Usuarios

- **Cajero / Vendedor:**
  - Registra ventas seleccionando productos del catálogo y cobrando con uno o varios medios de pago de forma inmediata.
- **Dueño del negocio:**
  - Accede a su negocio mediante credenciales seguras.
  - Administra el catálogo básico (productos con precio de venta y costo de referencia).
  - Consulta al cierre del día el reporte de facturación total por medio de pago y el margen bruto generado.

---

## 3. Propuesta de Valor

Una aplicación web progresiva (PWA) minimalista, robusta y multitenant:
- Inicio inmediato sin requisitos de apertura de turno de caja.
- Cobro transaccional e idempotente que previene ventas duplicadas.
- Reporte diario automático de recaudación y margen.

---

## 4. Alcance (IN) — Las 3 Funcionalidades Principales

### F1: Entrada a un negocio y catálogo básico
- Inicio de sesión mediante Supabase Auth.
- Acceso a un único negocio activo por usuario (aislamiento forzado por RLS en PostgreSQL mediante `business_id`).
- Gestión del catálogo básico: listado, creación y edición de productos (código/SKU, nombre, precio de venta en `Decimal`, costo de referencia unitario en `Decimal`).

### F2: Venta con varios medios de pago (Online primero e Idempotente)
- Selección de productos y armado de carrito en pantalla de venta.
- Cálculo de totales obligatoriamente en servidor con precisión monetaria (`Decimal`).
- Medios de pago combinables en una misma venta: Efectivo, Tarjeta, Transferencia / billetera virtual.
- Registro transaccional de venta con cabecera y detalle de ítems (`sale`, `sale_items`, `payments`).
- Garantía de idempotencia mediante identificador UUID generado por el cliente (`client_id`), previniendo ventas duplicadas ante reintentos.
- **Venta directa:** No requiere sesión de caja previa para registrar ventas.
- **Sin descuento de stock:** La venta no descuenta inventario en tiempo real en este lote.
- Comprobante / ticket digital en pantalla.

### F3: Reporte final diario de ventas y margen
- Consulta del consolidado diario para el dueño del negocio:
  - Total bruto facturado en la fecha.
  - Desglose de ingresos por medio de pago (Total Efectivo, Total Tarjetas, Total Transferencias).
  - Cantidad total de transacciones / tickets emitidos.
  - Costo de mercadería vendida acumulado en el día (calculado usando el costo congelado al momento de cada venta).
  - Margen bruto estimado (`Total Facturado - Costo Total`) y porcentaje de rentabilidad del día.

---

## 5. Fuera de Alcance (OUT) Justificado

| Funcionalidad descartada | Justificación |
|---|---|
| **Apertura y Cierre de caja (sesiones de caja)** | Excluido a solicitud explícita: elimina la necesidad de gestionar estados de sesión (`cash_sessions`), fondos iniciales y bloqueos de venta sin caja abierta. Las ventas se registran de forma directa. |
| **Arqueo de caja (ciego o estándar)** | Excluido a solicitud explícita: el control se enfoca en el reporte de recaudación por medio de pago. |
| **Descuento de stock en tiempo real / Kardex** | Excluido a solicitud explícita: simplifica la transacción de venta y evita bloqueos de concurrencia en inventario. |
| **Asistente en lenguaje natural con IA** | Funcionalidad auxiliar post-MVP. |
| **Cambio dinámico multi-negocio e invitaciones** | Un solo negocio activo por usuario en este lote. |
| **Detección de reuso de refresh token rotativo** | Uso de autenticación y refresco estándar de Supabase. |
| **Anulaciones de venta en interfaz** | Sin UI de anulación en MVP. |
| **Cola de sincronización offline con bloqueo multi-pestaña** | Enfoque online primero e idempotente. |
| **Facturación electrónica, OCR, imágenes de producto e impresión térmica** | Postergados a la v2. |
| **Ambientes separados de staging y producción** | Un único ambiente desplegado. |
