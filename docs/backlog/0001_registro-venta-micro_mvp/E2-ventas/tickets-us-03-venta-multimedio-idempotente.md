# Tickets Técnicos — US-03: Registro de Venta con Múltiples Medios de Pago, Stock e Idempotencia

---

### TICKET-06: Esquema de base de datos de ventas, líneas y pagos con RLS
- **Issue GitHub:** [#46](https://github.com/ninargue/registro-venta-micro/issues/46)
- **Alcance / Capa:** Base de datos (`backend/migrations`, `supabase`)
- **Talla:** `M` | **Riesgo:** Medio
- **Dependencias:** `TICKET-03`
- **Descripción:** Definir tablas `sales` (con columna `client_id` UNIQUE por negocio), `sale_items` (con `unit_price` y `unit_cost` congelados en `numeric(12,2)`) y `payments` (`payment_method`, `amount`).
- **Definición de Terminado (DoD):**
  - [ ] Migración de Alembic con RLS en `sales`, `sale_items` y `payments`.
  - [ ] Clave única de idempotencia `(business_id, client_id)`.
  - [ ] Test que verifica que dos inserciones con el mismo `client_id` no duplican registros.

---

### TICKET-07: Servicio transaccional e idempotente de ventas con descuento de stock
- **Issue GitHub:** [#47](https://github.com/ninargue/registro-venta-micro/issues/47)
- **Alcance / Capa:** Backend (`backend/app/modules/sales`)
- **Talla:** `L` | **Riesgo:** Medio
- **Dependencias:** `TICKET-06`
- **Descripción:** Implementar endpoint `POST /api/v1/sales` que reciba `client_id`, lista de ítems (`product_id`, `quantity`) y desglose de `payments`. Valida totales en `Decimal` (precios brutos sin impuestos), graba venta, líneas y pagos en una sola transacción atómica, y descuenta el stock de cada producto (`stock = stock - cantidad`) sin bloquear si el stock queda en negativo. Si el `client_id` ya existe, responde de forma idempotente sin re-descontar stock.
- **Definición de Terminado (DoD):**
  - [ ] Transacción ACID con rollback garantizado ante excepciones.
  - [ ] Deducción atómica de inventario por ítem vendido.
  - [ ] Permite venta con stock negativo transitorio sin rechazar la operación.
  - [ ] Recálculo estricto de totales en servidor usando `Decimal`.
  - [ ] Tests de idempotencia ante peticiones repetidas con idéntico `client_id`.

---

### TICKET-08: Pantalla de mostrador, carrito y cobro con vuelto en efectivo
- **Issue GitHub:** [#48](https://github.com/ninargue/registro-venta-micro/issues/48)
- **Alcance / Capa:** Frontend (`frontend/src/app`)
- **Talla:** `L` | **Riesgo:** Medio
- **Dependencias:** `TICKET-05`, `TICKET-07`
- **Descripción:** Desarrollar la interfaz táctil de mostrador en la PWA: armado ágil del carrito, visualización de total anunciado, selección de medios de pago combinables (efectivo con calculador de vuelto en cliente, tarjeta, transferencia/QR) y emisión directa de la venta enviando un UUID v4 como `client_id` persistido en el estado del carrito.
- **Definición de Terminado (DoD):**
  - [ ] Interfaz táctil optimizada para celular.
  - [ ] Calculador de vuelto en pagos en efectivo (ingreso de monto recibido y visualización de vuelto).
  - [ ] Generación automática y persistencia de UUID v4 por cada venta en preparación.
  - [ ] Ticket digital en pantalla con resumen de la venta completada.
