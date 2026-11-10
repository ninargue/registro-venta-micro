# Tickets Técnicos — US-01: Autenticación, Onboarding y Acceso al Negocio

---

### TICKET-01: Endpoint de autenticación, onboarding y contexto de negocio RLS
- **Issue GitHub:** [#39](https://github.com/ninargue/registro-venta-micro/issues/39)
- **Alcance / Capa:** Backend (`backend/app/modules/auth`)
- **Talla:** `M` | **Riesgo:** Medio
- **Dependencias:** Ninguna (base del sistema)
- **Descripción:** Implementar endpoints `POST /api/v1/auth/login` y `POST /api/v1/auth/onboarding`. Si el usuario no tiene comercio asignado tras autenticarse en Supabase Auth, `POST /api/v1/auth/onboarding` crea el registro en `businesses` (con nombre, `country` y `timezone`, ej. `America/Argentina/Buenos_Aires`) y lo asocia al usuario. Configurar middleware que inyecte `SET LOCAL app.current_business_id = '<uuid>'` en la sesión de base de datos.
- **Definición de Terminado (DoD):**
  - [ ] Rutas `/login` y `/onboarding` documentadas en OpenAPI.
  - [ ] Columna `timezone` en tabla `businesses` con valor resuelto por país.
  - [ ] Middleware que aplica RLS configurando `app.current_business_id`.
  - [ ] Tests de integración de login y flujo de onboarding.

---

### TICKET-02: Interfaz de Login, Onboarding y almacenamiento de sesión
- **Issue GitHub:** [#40](https://github.com/ninargue/registro-venta-micro/issues/40)
- **Alcance / Capa:** Frontend (`frontend/src/app`)
- **Talla:** `S` | **Riesgo:** Bajo
- **Dependencias:** `TICKET-01`
- **Descripción:** Crear la pantalla de login en la PWA con formulario de credenciales. Si el usuario no tiene comercio asignado, dirigir a pantalla simple de bienvenida/onboarding solicitando nombre de negocio y país, persistiendo el token y `business_id` en almacenamiento local seguro (`localStorage`).
- **Definición de Terminado (DoD):**
  - [ ] Formulario accesible con validación de campos obligatorios.
  - [ ] Pantalla/modal de onboarding para primer acceso.
  - [ ] Redirección automática al mostrador al completar la autenticación.
