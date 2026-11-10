# US-03: Registro de Venta con Múltiples Medios de Pago, Stock e Idempotencia

**Épica:** E2-ventas  
**Estado:** Consolidada v0.2  
**GitHub Issue:** [#45](https://github.com/ninargue/registro-venta-micro/issues/45)  

---

## 1. Descripción
**Como** dueño del micronegocio en el mostrador,  
**quiero** totalizar la compra de productos, cobrar admitiendo medios de pago combinados con cálculo de vuelto en efectivo y emitir la venta directamente,  
**para** completar transacciones en pocos toques, actualizar el stock de forma atómica y evitar ventas duplicadas ante reintentos.

---

## 2. Criterios de Aceptación (Given / When / Then)

### Escenario 1: Venta exitosa con un medio de pago y descuento de stock
- **Dado** que el usuario está autenticado en su negocio y tiene productos en el carrito,
- **cuando** confirma la venta pagada con un medio de pago (ej. efectivo),
- **entonces** el servidor recalcula subtotales en `Decimal` sobre precios brutos (sin impuestos),
- **y** registra de forma atómica la venta (`sale`), sus líneas (`sale_items`) congelando precio y costo, y el pago (`payments`),
- **y** ejecuta la deducción atómica de stock en cada producto (`stock = stock - cantidad`),
- **y** emite el comprobante de venta (HTTP 201).

### Escenario 2: Pago en efectivo con cálculo de vuelto en UI
- **Dado** una venta con total de \$3.400,
- **cuando** el cliente entrega un billete de \$5.000,
- **entonces** la interfaz calcula y muestra en pantalla "Vuelto: \$1.600",
- **y** al confirmar, envía al backend como pago en efectivo el importe neto exacto (\$3.400).

### Escenario 3: Venta con pago mixto (Efectivo + Transferencia/Tarjeta)
- **Dado** una venta total de \$1.000,
- **cuando** el cliente abona \$400 en efectivo y \$600 con transferencia QR,
- **entonces** el servidor valida que la suma de los pagos coincida exactamente con el total de la venta,
- **y** almacena ambos registros de pago.

### Escenario 4: Venta con stock insuficiente (no bloqueante)
- **Dado** que un producto tiene stock = 2 y el cliente compra 3 unidades,
- **cuando** se procesa la venta,
- **entonces** según la regla de oro del mostrador (la venta nunca se rechaza), la venta se procesa con éxito y el stock del producto queda en -1.

### Escenario 5: Idempotencia ante reintentos de red
- **Dado** que el cliente emite la venta con un identificador único `client_id` (UUID v4) persistido en el estado del carrito,
- **cuando** la respuesta de red falla y el cliente reintenta la misma venta con idéntico `client_id`,
- **entonces** el backend responde la venta ya registrada sin duplicar registros ni volver a descontar inventario (HTTP 200/201 idempotente).

---

## 3. Reglas de Negocio
- Toda venta congela `unit_price` y `unit_cost` en `sale_items`.
- Precios brutos: sin desglose de impuestos en este MVP.
- Venta irreversible en este lote: no hay anulación en UI ni notas de crédito; los errores de tipeo se verifican en pantalla antes de confirmar.
