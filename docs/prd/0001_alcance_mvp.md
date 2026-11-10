# Alcance — registro-venta-micro (mvp)

> Fecha: 2026-11-10  
> Basado en: Revisión de la Primera Entrega y auditoría adversarial consolidada  
> Estado: Consolidado v0.2 Definitivo

---

## 1. Problema

Los micronegocios (kioscos, ferreterías de barrio, almacenes y puestos de mercado) necesitan agilidad y control básico:
1. **Cobro ágil y ordenado:** Registrar ventas en pocos toques desde el celular, admitiendo medios de pago combinados y calculando el vuelto en efectivo de forma inmediata.
2. **Control de stock simple:** Actualizar el inventario con cada venta sin trabas de stock negativo que bloqueen el mostrador.
3. **Margen de ganancia visible en hora local:** Conocer al final del día cuánto se vendió y cuál fue la ganancia bruta estimada según la zona horaria del comercio (`timezone`).

Para este lote, el alcance se mantiene limpio: no hay aperturas ni cierres de turnos de caja, ni notas de crédito/anulaciones complejas, ni desglose tributario de impuestos.

---

## 2. Usuarios

- **Dueño del micronegocio (Usuario único del MVP):**
  - Actor único en esta versión: atiende el mostrador, administra su comercio y revisa los números. No existen roles diferenciados ni gestión de empleados/cajeros.
  - Accede mediante credenciales seguras (o crea su comercio en el onboarding inicial con país y zona horaria).
  - Administra el catálogo básico (productos con precio de venta, costo de referencia y stock).
  - Registra las ventas directamente en el mostrador seleccionando productos, aplicando pagos multimedio y calculando vuelto en efectivo.
  - Consulta al cierre del día el reporte de facturación total por medio de pago y el margen bruto en su zona horaria local.

---

## 3. Propuesta de Valor

Una aplicación web progresiva (PWA) minimalista, robusta y multitenant:
- Inicio inmediato y onboarding simple (creación de comercio en primer acceso).
- Cobro transaccional e idempotente con cálculo de vuelto en efectivo y descuento de stock.
- Reporte diario automático de recaudación y margen con fecha local del comercio.

---

## 4. Alcance (IN) — Las 3 Funcionalidades Principales

### F1: Entrada a un negocio y catálogo básico
- Inicio de sesión mediante Supabase Auth.
- **Onboarding de negocio:** Si el usuario es nuevo y no tiene comercio, la pantalla pide nombre del comercio y país (`country`/`timezone`) creando el registro vía `POST /api/v1/auth/onboarding` sin pedir credenciales de nuevo.
- Aislamiento multitenant forzado por RLS en PostgreSQL mediante `business_id`.
- Gestión del catálogo básico: listado, creación y edición de productos (código/SKU opcional, nombre obligatorio, precio de venta en `Decimal`, costo de referencia unitario en `Decimal` y stock numérico inicial).

### F2: Venta con varios medios de pago e idempotencia (con actualización de stock)
- Selección de productos y armado de carrito en pantalla de venta.
- Cálculo de totales obligatoriamente en servidor con precisión monetaria (`Decimal`) sobre precios brutos (sin impuestos).
- Medios de pago combinables en una misma venta: Efectivo (con calculador de vuelto en cliente mostrando monto recibido vs. vuelto), Tarjeta, Transferencia / billetera virtual.
- Totalización anunciada al cliente: la venta se confirma y se valida que los pagos igualen al total anunciado.
- Registro transaccional de venta con cabecera y detalle de ítems (`sale`, `sale_items`, `payments`).
- **Actualización de stock atómica:** En la misma transacción de venta, se descuenta la cantidad vendida del stock de cada producto (`stock = stock - cantidad`). Siguiendo la regla del mostrador, la venta nunca se rechaza por stock insuficiente (permite stock negativo transitorio).
- Garantía de idempotencia mediante identificador UUID generado por el cliente (`client_id`) persistido en el carrito.
- Comprobante / ticket digital en pantalla.

### F3: Reporte final diario de ventas y margen (Hora local del tenant)
- Consulta del consolidado diario agrupado por la zona horaria del comercio (`(created_at AT TIME ZONE b.timezone)::date = :fecha`):
  - Total bruto facturado en la fecha.
  - Desglose de ingresos por medio de pago (Total Efectivo, Total Tarjetas, Total Transferencias).
  - Cantidad total de transacciones completadas.
  - Costo de mercadería vendida acumulado en el día (sumando `quantity * unit_cost` congelado al momento de cada venta).
  - Margen bruto estimado (`Total Facturado - Costo Total`) y porcentaje de ganancia.

---

## 5. Fuera de Alcance (OUT) Justificado

| Funcionalidad descartada | Justificación |
|---|---|
| **Apertura y Cierre de caja (sesiones de caja)** | Elimina gestión de estados (`cash_sessions`), fondos iniciales y bloqueos de venta sin caja abierta. Las ventas se registran de forma directa. |
| **Arqueo de caja (ciego o estándar)** | El control se enfoca en el reporte de recaudación por medio de pago. |
| **Anulaciones de venta / Notas de crédito y débito** | Contablemente las ventas se ajustan por notas de crédito o débito, lo cual agrega complejidad fiscal y de estados. Los errores de tipeo se corrigen antes de registrar el cobro en mostrador. |
| **Motor impositivo / cálculo de impuestos (IVA)** | Opera con precios brutos finales, alineado a la operativa simple del micronegocio. |
| **Gestión de empleados, cajeros y roles múltiples** | Simplificado a un usuario único (Dueño del micronegocio). No hay altas de empleados, roles `cashier`/`admin`, ni perfiles diferenciados en este MVP. |
| **Asistente en lenguaje natural con IA** | Funcionalidad auxiliar post-MVP. |
| **Cambio dinámico multi-negocio e invitaciones** | Un solo negocio activo por usuario en este lote. |
| **Detección de reuso de refresh token rotativo** | Uso de autenticación y refresco estándar de Supabase. |
| **Cola de sincronización offline con bloqueo multi-pestaña** | Enfoque online primero e idempotente. |
| **Facturación electrónica, OCR, imágenes de producto e impresión térmica** | Postergados a la v2. |
| **Ambientes separados de staging y producción** | Un único ambiente desplegado. |
