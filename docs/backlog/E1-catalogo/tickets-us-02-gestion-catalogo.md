# Tickets Técnicos — US-02: Carga y Gestión Básica de Catálogo

---

### TICKET-03: Esquema de base de datos de productos con políticas RLS
- **Alcance / Capa:** Base de datos (`backend/migrations`, `supabase`)
- **Talla:** `S` | **Riesgo:** Bajo
- **Dependencias:** `TICKET-01`
- **Descripción:** Crear o refinar la tabla `products` con foránea `business_id`, columnas `code`, `name`, `sale_price` (`numeric(12,2)`), `cost_price` (`numeric(12,2)`), `stock` (`numeric(12,2)`), y política RLS habilitada.
- **Definición de Terminado (DoD):**
  - [ ] Migración de Alembic aplicada y verificada.
  - [ ] Test automatizado que falla si la tabla `products` no tiene RLS forzada o si un tenant puede consultar productos de otro.
  - [ ] Campos monetarios en tipo `numeric(12,2)`, prohibido el uso de `float`.

---

### TICKET-04: API REST de Catálogo de Productos
- **Alcance / Capa:** Backend (`backend/app/modules/catalog`)
- **Talla:** `M` | **Riesgo:** Bajo
- **Dependencias:** `TICKET-03`
- **Descripción:** Implementar endpoints `GET /api/v1/catalog/products` (con búsqueda por texto) y `POST /api/v1/catalog/products` para alta de ítems.
- **Definición de Terminado (DoD):**
  - [ ] Rutas documentadas en OpenAPI.
  - [ ] Esquemas Pydantic validando precios y costos positivos en `Decimal`.
  - [ ] Tests de integración de listado y creación.

---

### TICKET-05: Vista de administración y selector de productos en frontend
- **Alcance / Capa:** Frontend (`frontend/src/app`)
- **Talla:** `M` | **Riesgo:** Bajo
- **Dependencias:** `TICKET-04`
- **Descripción:** Crear componente de catálogo en la PWA para listar y registrar productos con buscador reactivo.
- **Definición de Terminado (DoD):**
  - [ ] Grilla táctil / lista de productos con nombre y precio.
  - [ ] Formulario simple para alta y edición de producto.
  - [ ] Feedback visual de carga y errores de validación.
