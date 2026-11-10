# US-03: Registro de Venta con Múltiples Medios de Pago e Idempotencia

**Épica:** E2-ventas  
**Estado:** Lista para refinamiento técnico  

---

## 1. Descripción
**Como** cajero del micronegocio,  
**quiero** registrar los productos seleccionados por el cliente, calcular el total y cobrar admitiendo uno o varios medios de pago simultáneos,  
**para** completar transacciones de forma ágil y segura sin duplicación por fallas de conexión o reintentos, y sin requerir aperturas de caja previas.

---

## 2. Criterios de Aceptación (Given / When / Then)

### Escenario 1: Venta exitosa directa con un solo medio de pago
- **Dado** que el usuario está autenticado en su negocio,
- **y** tiene productos agregados al carrito,
- **cuando** confirma la venta pagada en su totalidad con efectivo,
- **entonces** el servidor recalcula subtotales en `Decimal`,
- **y** genera el registro de venta (`sale`), sus líneas (`sale_items`) con el precio y costo unitario congelados en ese instante,
- **y** registra el pago correspondiente (`payments`),
- **y** responde con el comprobante digital de la venta (HTTP 201) sin requerir sesión de caja abierta ni modificar el stock en inventario.

### Escenario 2: Venta con pago mixto (Efectivo + Transferencia/Tarjeta)
- **Dado** una venta con total de \$1.000,
- **cuando** el cliente abona \$400 en efectivo y \$600 con transferencia bancaria,
- **entonces** el servidor valida que la suma de los pagos coincida exactamente con el total recalculado,
- **y** almacena los dos registros de pago vinculados a la venta.

### Escenario 3: Idempotencia ante reintentos de red
- **Dado** que el cliente envía una venta con un identificador único `client_id` (UUID v4),
- **y** la petición se procesó exitosamente pero la respuesta HTTP no llegó al cliente debido a un corte momentáneo,
- **cuando** el cliente reintenta enviar la misma venta con idéntico `client_id`,
- **entonces** el backend detecta la clave existente, no duplica el cobro ni registros de venta, y responde con la venta original registrada (HTTP 200/201 idempotente).

---

## 3. Reglas de Negocio
- Cada línea de venta congela el `unit_price` y el `unit_cost` al momento de la venta para garantizar la fidelidad del cálculo de margen histórico.
- Todos los cálculos monetarios se realizan en el servidor usando tipos `Decimal` / `numeric(12,2)`.
- La suma de los montos de pago debe igualar exactamente al total de la venta.
- No se requiere sesión de caja previa ni se descuenta inventario.

---

## 4. Fuera de Alcance de esta Historia
- Deducción de stock en tiempo real.
- Bloqueo o validación de sesión de caja activa.
- Anulación o devolución de venta desde la UI.
- Emisión de factura fiscal electrónica e impresión térmica.
