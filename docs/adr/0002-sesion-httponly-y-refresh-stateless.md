# ADR-0002: Gestión de sesión mediante cookies HttpOnly y renovación sin estado

- **Estado:** Aceptado
- **Fecha:** 2026-11-17
- **Autores:** Nindirí Armenta Guerrero
- **Issue / PR:** #39, #55 / PR #52

## Contexto

La aplicación cliente (PWA) no debe comunicarse directamente con el proveedor externo de autenticación ni almacenar credenciales o tokens de sesión en almacenamiento accesible desde scripts del navegador (como almacenamiento local), para reducir la superficie de ataque ante vulnerabilidades de inyección de scripts. Al mismo tiempo, las sesiones de mostrador requieren continuidad operativa sin obligar al usuario a reingresar credenciales cada pocos minutos ni perder su estado al recargar la pestaña.

## Opciones consideradas

| Opción | Ventajas | Desventajas |
|--------|----------|-------------|
| A. Tokens firmados de acceso y renovación en cookies `HttpOnly` sin estado en base de datos | Cero latencia adicional de almacenamiento de sesiones en base de datos, implementación simple y compatible con el alcance MVP | No permite revocación individual de tokens de renovación antes de su expiración ni detección de reuso |
| B. Tokens de renovación rotativos persistidos en base de datos con tabla de revocación y detección de reuso | Permite revocación inmediata por dispositivo y detección de compromiso de credenciales | Añade tablas, migraciones, políticas de aislamiento adicionales y mayor complejidad operativa fuera del alcance MVP |

## Decisión

Se adopta la **Opción A** para el MVP:
1. **Delegación exclusiva de credenciales:** El backend verifica las credenciales contra el proveedor de autenticación externo y emite sus propios tokens firmados de sesión, sin exponer llaves privilegiadas ni permitir contacto directo desde el navegador.
2. **Cookies de sesión seguras:** Los tokens de acceso (corta duración) y de renovación (larga duración) se entregan exclusivamente en cookies marcadas como solo lectura HTTP, política estricta de mismo sitio y transmisión segura obligatoria en producción.
3. **Discriminación de propósito:** Cada token declara explícitamente su tipo de uso para impedir que un token de renovación sea aceptado como token de acceso o viceversa.
4. **Ciclo completo de sesión en API:** Se proveen operaciones explícitas para consultar la sesión activa al recargar la aplicación, renovar los tokens consultando la membresía vigente en base de datos y cerrar la sesión expirando ambas cookies.

## Consecuencias

- **Positivas:** Protege los tokens frente a lectura desde scripts del navegador, mantiene la interfaz desacoplada del proveedor de identidad y permite rehidratar o renovar la sesión de forma transparente para el usuario en mostrador.
- **Negativas / trade-offs asumidos:** Un token de renovación emitido sigue siendo válido hasta su expiración natural si fue extraído antes de caducar, ya que el cierre de sesión solo elimina las cookies en el cliente.
- **Riesgos y mitigaciones:** Se mitiga manteniendo una vigencia corta para el token de acceso, restringiendo los algoritmos criptográficos permitidos a variantes simétricas seguras, exigiendo longitud mínima de clave secreta y bloqueando el uso de cookies sin cifrado en producción.

## Cumplimiento

- **Tests:** Pruebas de integración que validan emisión de cookies con atributos de seguridad, consulta de sesión activa, limpieza de cookies al cerrar sesión, renovación exitosa y rechazo cruzado entre tipos de token.
- **Base de datos / código:** Validación estricta de configuración de seguridad al arranque y validación de consistencia entre comercio y rol en los tokens de acceso.
- **CI / revisión en PR:** Ejecución de suite de integración en CI y revisión de atributos de cookies en el flujo de autenticación.

## Referencias

- [ADR-0001: Rol de ejecución dedicado sin omisión de RLS y revocación de acceso directo en base de datos](0001-rol-runtime-y-endurecimiento-rls.md)
- Alcance MVP del proyecto (`docs/prd/0001_alcance_mvp.md`)
