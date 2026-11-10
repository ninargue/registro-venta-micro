# US-01: Autenticación y Selección de Negocio

**Épica:** E1-catalogo  
**Estado:** Lista para refinamiento técnico  

---

## 1. Descripción
**Como** dueño o cajero de un micronegocio,  
**quiero** iniciar sesión con mis credenciales y acceder al entorno de mi negocio,  
**para** operar el punto de venta de forma segura sin riesgo de ver ni alterar datos de otros comercios.

---

## 2. Criterios de Aceptación (Given / When / Then)

### Escenario 1: Inicio de sesión exitoso con negocio vinculado
- **Dado** que soy un usuario registrado con credenciales válidas en Supabase Auth,
- **y** tengo un negocio asignado (`business_id`),
- **cuando** envío mis credenciales al endpoint de login,
- **entonces** el sistema me autentica, establece la sesión y me retorna el token JWT junto con los datos de mi negocio (`id`, `nombre`),
- **y** todas las peticiones subsecuentes operan bajo el contexto RLS de ese `business_id`.

### Escenario 2: Intento de acceso con credenciales inválidas
- **Dado** que ingreso un email o contraseña erróneos,
- **cuando** intento iniciar sesión,
- **entonces** el sistema rechaza la petición con código HTTP 401 y un mensaje claro de error sin filtrar detalles internos.

### Escenario 3: Aislamiento estricto de datos (RLS)
- **Dado** que estoy autenticado en el negocio A,
- **cuando** intento consultar un recurso perteneciente al negocio B,
- **entonces** la base de datos no retorna registros (o HTTP 404), garantizando aislamiento total a nivel de motor PostgreSQL.

---

## 3. Reglas de Negocio
- La relación en este MVP es de un único negocio activo por usuario registrado.
- El `business_id` se extrae exclusivamente del token o contexto de sesión seguro en el servidor; nunca se acepta como parámetro libre en el body de peticiones de clientes.

---

## 4. Fuera de Alcance de esta Historia
- Registro público libre sin invitación/asociación previa.
- Cambio entre múltiples negocios en caliente desde la interfaz.
- Recuperación de contraseña por SMS/WhatsApp.
