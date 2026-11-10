# Tickets Técnicos — US-03: Registro de Venta con Múltiples Medios de Pago e Idempotencia

---

### TICKET-06: Esquema de base de datos de ventas, líneas y pagos con RLS
- **Alcance / Capa:** Base de datos (`backend/migrations`, `supabase`)
- **Talla:** `M` | **Riesgo:** Medio
- **Dependencias:** `TICKET-03`
- **Descripción:** Definir tablas `sales` (con columna `client_id` UNIQUE por negocio), `sale_items` (con `unit_price` y `unit_cost` congelados en `numeric(12,2)`) y `payments` (`payment_method`, `amount`).
- **Definición de Terminado (DoD):**
  - [ ] Migración de Alembic con RLS en `sales`, `sale_items` y `payments`.
  - [ ] Clave única de idempotencia `(business_id, client_id)`.
  - [ ] Test que verifica que dos inserciones con el mismo `client_id` no duplican registros.

---

### TICKET-07: Servicio transaccional e idempotente de ventas en backend
- **Alcance / Capa:** Backend (`backend/app/modules/sales`)
- **Talla:** `L` | **Riesgo:** Medio
- **Dependencias:** `TICKET-06`
- **Descripción:** Implementar endpoint `POST /api/v1/sales` que reciba `client_id`, lista de ítems (`product_id`, `quantity`) y desglose de `payments`. Valida cálculo de totales en `Decimal` en el servidor, graba venta, líneas y pagos en una sola transacción atómica sin modificar stock ni requerir sesión de caja. Si el `client_id` ya existe, responde la venta registrada de forma idempotente.
- **Definición de Terminado (DoD):**
  - [ ] Transacción ACID con rollback garantizado ante cualquier excepción.
  - [ ] Recálculo estricto de subtotales en servidor usando `Decimal`.
  - [ ] Validación de coincidencia exacta entre monto total y suma de medios de pago.
  - [ ] Tests de idempotencia ante peticiones repetidas con idéntico `client_id`.

---

### TICKET-08: Pantalla de mostrador, carrito y cobro multimedio en frontend
- **Alcance / Capa:** Frontend (`frontend/src/app`)
- **Talla:** `L` | **Riesgo:** Medio
- **Dependencias:** `TICKET-05`, `TICKET-07`
- **Descripción:** Desarrollar la interfaz táctil de mostrador en la PWA: armado ágil del carrito, visualización de total, selección de medios de pago combinables (efectivo, tarjeta, transferencia/QR) y emisión directa de la venta enviando un UUID v4 como `client_id`.
- **Definición de Terminado (DoD):**
  - [ ] Interfaz táctil optimizada para celular.
  - [ ] Generación automática de UUID v4 para cada intento de venta.
  - [ ] Modal de cobro con validación de montos antes del envío.
  - [ ] Ticket digital en pantalla con resumen de la venta completada.
