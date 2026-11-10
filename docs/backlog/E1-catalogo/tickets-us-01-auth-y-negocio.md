# Tickets Técnicos — US-01: Autenticación y Acceso al Negocio

---

### TICKET-01: Endpoint de autenticación y emisión de contexto de negocio
- **Alcance / Capa:** Backend (`backend/app/modules/auth`)
- **Talla:** `M` | **Riesgo:** Medio
- **Dependencias:** Ninguna (base del sistema)
- **Descripción:** Implementar el endpoint `POST /api/v1/auth/login` que valide credenciales con Supabase Auth, resuelva el `business_id` del usuario en la base de datos y emita el JWT con los claims de sesión.
- **Definición de Terminado (DoD):**
  - [ ] Ruta `/api/v1/auth/login` documentada en OpenAPI.
  - [ ] Middleware que inyecta `business_id` en `request.state` y ejecuta `SET LOCAL app.current_business_id = '<uuid>'` en la sesión de base de datos.
  - [ ] Tests de integración con credenciales válidas e inválidas.

---

### TICKET-02: Interfaz de Login y almacenamiento de sesión en cliente
- **Alcance / Capa:** Frontend (`frontend/src/app`)
- **Talla:** `S` | **Riesgo:** Bajo
- **Dependencias:** `TICKET-01`
- **Descripción:** Crear la pantalla de login en la PWA con formulario de email y contraseña, guardando el token y `business_id` en almacenamiento local seguro (`localStorage` / estado reactivo).
- **Definición de Terminado (DoD):**
  - [ ] Formulario accesible con validación de campos obligatorios.
  - [ ] Manejo de errores de credenciales (HTTP 401).
  - [ ] Redirección automática al mostrador al autenticar con éxito.
