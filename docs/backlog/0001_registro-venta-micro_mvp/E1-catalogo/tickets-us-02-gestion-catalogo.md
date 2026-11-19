# Tickets Técnicos — US-02: Carga y Gestión Básica de Catálogo con Stock

---

### TICKET-03: Esquema de base de datos de productos con políticas RLS y stock
- **Issue GitHub:** [#42](https://github.com/ninargue/registro-venta-micro/issues/42)
- **Alcance / Capa:** Base de datos (`backend/migrations`, `supabase`)
- **Talla:** `S` | **Riesgo:** Bajo
- **Dependencias:** `TICKET-01`
- **Descripción:** Crear o refinar la tabla `products` con foránea `business_id`, columnas `code`, `name`, `sale_price` (`numeric(12,2)`), `cost_price` (`numeric(12,2)`), `stock` (`numeric(12,2)`), y política RLS habilitada.
- **Definición de Terminado (DoD):**
  - [ ] Migración de Alembic aplicada y verificada.
  - [ ] Test automatizado que verifica que la tabla `products` tiene RLS forzada y que un tenant no puede leer ítems de otro.
  - [ ] Campos monetarios y de stock en tipo `numeric(12,2)`, prohibido el uso de `float`.

---

### TICKET-04: API REST de Catálogo de Productos con Stock
- **Issue GitHub:** [#43](https://github.com/ninargue/registro-venta-micro/issues/43)
- **Alcance / Capa:** Backend (`backend/app/modules/catalog`)
- **Talla:** `M` | **Riesgo:** Bajo
- **Dependencias:** `TICKET-03`
- **Descripción:** Implementar endpoints `GET /api/v1/catalog/products` (con buscador por texto) y `POST /api/v1/catalog/products` para alta de ítems con precio de venta, costo y stock inicial.
- **Definición de Terminado (DoD):**
  - [ ] Rutas documentadas en OpenAPI.
  - [ ] Esquemas Pydantic validando precios brutos y stock en `Decimal`.
  - [ ] Tests de integración de listado y creación.

---

### TICKET-05: Vista de administración y selector de productos en frontend
- **Issue GitHub:** [#44](https://github.com/ninargue/registro-venta-micro/issues/44)
- **Alcance / Capa:** Frontend (`frontend/src/app`)
- **Talla:** `M` | **Riesgo:** Bajo
- **Dependencias:** `TICKET-04`
- **Descripción:** Crear componente de catálogo en la PWA para listar y registrar productos con buscador reactivo y visualización de stock.
- **Definición de Terminado (DoD):**
  - [ ] Grilla táctil / lista de productos con nombre, precio y stock.
  - [ ] Formulario simple para alta y edición de producto.
  - [ ] Feedback visual de carga y errores de validación.
