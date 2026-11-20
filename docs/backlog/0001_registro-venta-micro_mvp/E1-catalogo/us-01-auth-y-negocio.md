# US-01: Autenticación, Onboarding y Acceso al Negocio

**Épica:** E1-catalogo  
**Estado:** Consolidada v0.2  
**GitHub Issue:** [#38](https://github.com/ninargue/registro-venta-micro/issues/38)  

---

## 1. Descripción
**Como** dueño de un micronegocio,  
**quiero** iniciar sesión con mis credenciales (o registrar mi comercio en el onboarding si es mi primer acceso),  
**para** operar el punto de venta de forma segura con aislamiento multitenant estricto por RLS.

---

## 2. Criterios de Aceptación (Given / When / Then)

### Escenario 1: Inicio de sesión exitoso con negocio existente
- **Dado** que soy un usuario registrado en Supabase Auth con un negocio ya asignado,
- **cuando** envío mis credenciales a `/api/v1/auth/login`,
- **entonces** el sistema me autentica, resuelve mi `business_id` y emite el token de sesión,
- **y** todas las peticiones posteriores inyectan `business_id` ejecutando `SET LOCAL app.current_business_id` en PostgreSQL.

### Escenario 2: Onboarding de primer acceso (usuario nuevo sin comercio)
- **Dado** que un usuario se autentica exitosamente pero no tiene ningún comercio asociado,
- **cuando** la PWA le solicita el nombre del comercio y país (`country`/`timezone`),
- **y** se envía la petición a `POST /api/v1/auth/onboarding`,
- **entonces** el backend crea la entidad en `businesses` con su país y zona horaria (ej. `America/Argentina/Buenos_Aires`),
- **y** vincula al usuario como dueño, retornando la sesión lista para operar sin pedir credenciales nuevamente.

### Escenario 3: Intento de acceso con credenciales inválidas
- **Dado** que ingreso credenciales incorrectas,
- **cuando** intento autenticarme,
- **entonces** el sistema responde HTTP 401 con mensaje genérico de error.

---

## 3. Reglas de Negocio
- Cada usuario opera un único comercio en este lote (usuario único: Dueño del micronegocio; empleados y roles adicionales quedan fuera de scope).
- El `business_id` se extrae únicamente del token o contexto seguro en backend, jamás del body de las peticiones.
- La zona horaria del comercio se infiere del país registrado durante el onboarding.
