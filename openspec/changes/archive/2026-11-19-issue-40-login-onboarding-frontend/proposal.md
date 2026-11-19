# Proposal: Interfaz de Login, Onboarding y almacenamiento de sesión

Ticket: US-01-T02 | Issue: #40 (https://github.com/ninargue/registro-venta-micro/issues/40) | Capa: frontend

## Why

El backend ya expone los endpoints de autenticación, onboarding y ciclo de sesión con cookies `HttpOnly` (`issue-55`), pero la PWA únicamente renderiza una ruta raíz mínima (`/`) sin acceso de usuario ni creación inicial de comercio. Se necesita la interfaz cliente accesible de login, onboarding de primer acceso y gestión segura de sesión para habilitar la entrada multitenant al mostrador.

## What Changes

- **Pantalla `/login` accesible y responsiva:** Formulario de correo y contraseña alineado con `docs/ui/auth-onboarding-ui-spec.json` y tokens de `frontend/src/index.css` (ergonomía táctil `>= 48px`, soporte claro/oscuro, validación cliente y alertas accesibles para errores `401`/`422`/`429`/`502`/`503`).
- **Modal accesible de Onboarding:** Al autenticarse o rehidratar sesión con `requires_onboarding: true`, despliega diálogo modal bloqueante (`role="dialog"`, `aria-modal="true"`) solicitando nombre del negocio y país (`SUPPORTED_COUNTRIES`), enviando `POST /api/v1/auth/onboarding`.
- **Cliente API y ciclo de sesión con cookies `HttpOnly`:** Todas las peticiones usan `credentials: "include"`. Rehidratación inicial vía `GET /api/v1/auth/me`, renovación ante `401` vía `POST /api/v1/auth/refresh` y cierre vía `POST /api/v1/auth/logout`.
- **Persistencia acotada de contexto:** Prohibido almacenar JWTs en `localStorage`; únicamente se persisten metadatos públicos no sensibles (`user.id`, `user.email`, `business.id`, `business.name`, `country`, `timezone`, `role`) sincronizados con el estado cliente.
- **Protección de rutas y redirección automática:** Redirección a `/` tras login completo (`requires_onboarding: false`) u onboarding exitoso (`201`), y redirección a `/login` si no existe sesión válida.

## Capabilities

### New Capabilities
- `auth-onboarding-ui`: Flujo frontend de autenticación, modal de onboarding inicial de comercio, manejo de sesión vía cookies `HttpOnly`, persistencia pública de contexto y protección de rutas de la PWA.

### Modified Capabilities
<!-- Sin cambios a requisitos de backend/API existentes en openspec/specs/auth-onboarding/spec.md -->

## Non-goals

- Pantallas de catálogo de productos, carrito/mostrador de ventas o reportes diarios (tickets `US-02`–`US-04`).
- Registro de nuevos usuarios, recuperación de contraseña o invitación de cajeros/roles adicionales (usuario único dueño del micronegocio en MVP).
- Cola offline de ventas en Dexie o configuración de Service Worker con Workbox (`vite-plugin-pwa` se habilita junto con la funcionalidad offline de catálogo/ventas).
- Edición del contrato `docs/api/openapi.json` o código de backend/base de datos.

## Impact

- **Código afectado:** `frontend/src/app/` (router, providers, guardas), `frontend/src/features/auth/` (cliente API, estado de sesión, vistas y componentes), `frontend/src/shared/ui/` (primitivas accesibles reutilizables), `frontend/src/test/` y `frontend/tests/e2e/`.
- **Contratos consumidos:** `POST /api/v1/auth/login`, `POST /api/v1/auth/onboarding`, `GET /api/v1/auth/me`, `POST /api/v1/auth/refresh`, `POST /api/v1/auth/logout` en `docs/api/openapi.json`.
- **Impacto offline/PWA:** Login y onboarding requieren conectividad (no se autentican ni crean comercios offline). La app mantiene únicamente metadatos públicos de contexto para renderizado rápido mientras `HttpOnly` cookies y `GET /api/v1/auth/me` validan la sesión; sin almacenamiento en IndexedDB/Dexie ni registro de Service Worker en este cambio.
