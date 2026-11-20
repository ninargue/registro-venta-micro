# ADR-0001: Rol de ejecución dedicado sin omisión de RLS y revocación de acceso directo en base de datos

- **Estado:** Aceptado
- **Fecha:** 2026-11-17
- **Autores:** Nindirí Armenta Guerrero
- **Issue / PR:** #53, #54 / PR #52

## Contexto

El sistema opera con PostgreSQL administrado y aislamiento multi-tenant mediante Row-Level Security (RLS) forzada sobre las tablas de negocio. En la implementación inicial se detectaron dos riesgos estructurales:
1. La conexión de la API en tiempo de ejecución compartía el mismo rol administrativo usado para migraciones, el cual posee privilegios para omitir políticas RLS; ante cualquier consulta fuera de contexto o posterior al cierre de una transacción, el acceso quedaba expuesto sin aislamiento.
2. Los roles predeterminados de acceso directo a la plataforma de base de datos conservaban permisos amplios sobre las tablas de comercios y membresías, permitiendo inserciones o truncados directos omitiendo la lógica de validación del backend.

## Opciones consideradas

| Opción | Ventajas | Desventajas |
|--------|----------|-------------|
| A. Conectar con el rol administrativo y confiar únicamente en el cambio temporal de rol por transacción | No requiere gestionar credenciales adicionales | Arquitectura abierta ante fallos si una ruta omite fijar el contexto o ejecuta consultas tras confirmar la transacción |
| B. Separar el rol de migraciones del rol de ejecución sin privilegios de omisión de RLS, y revocar todo acceso a roles públicos y externos | Garantiza aislamiento por defecto incluso ante errores de programación y bloquea el acceso directo a tablas operativas | Requiere provisionar un rol adicional y configurar cadenas de conexión diferenciadas entre migraciones y ejecución |

## Decisión

Se adopta la **Opción B**:
1. **Separación de roles de base de datos:** Las migraciones se ejecutan con un rol administrativo exclusivo, mientras que el servicio backend en tiempo de ejecución se conecta con un rol dedicado sin privilegios de superusuario, creación de objetos ni omisión de RLS.
2. **Revocación total de acceso directo:** Se revocan todos los permisos sobre las tablas de comercios y membresías para el acceso público, anónimo y autenticado directo de la plataforma de base de datos, canalizando toda lectura y escritura exclusivamente a través del backend.
3. **Contexto obligatorio y limpieza transaccional:** Las políticas de inserción durante el alta de un comercio exigen que tanto la identidad del usuario como el identificador del comercio estén presentes y coincidan en el contexto transaccional, y cualquier contexto de solo-usuario limpia el identificador de comercio residual.
4. **Unicidad de membresía en el MVP:** Cada usuario pertenece a un único comercio en la etapa MVP, restringiendo además las modificaciones y bajas de membresías al rol de propietario.

## Consecuencias

- **Positivas:** Elimina el riesgo de exposición entre comercios ante olvidos en nuevos endpoints, impide el vaciado de tablas desde roles sin privilegios y bloquea el alta directa de comercios saltándose las validaciones del servidor.
- **Negativas / trade-offs asumidos:** Exige mantener credenciales separadas entre el proceso de migración y el proceso de ejecución de la API, además de limitar temporalmente a los usuarios a un único comercio hasta que se habilite soporte multi-comercio.
- **Riesgos y mitigaciones:** Una nueva tabla operativa podría heredar permisos abiertos si se omite en futuras migraciones; se mitiga exigiendo pruebas automáticas de aislamiento y de denegación de permisos en cada migración.

## Cumplimiento

- **Tests:** Pruebas de integración que verifican la existencia y atributos restrictivos del rol de ejecución, el rechazo de inserciones sin contexto completo, la imposibilidad de truncar tablas y el aislamiento entre comercios.
- **Base de datos / código:** Políticas RLS explícitas para lectura, inserción, actualización y borrado en las tablas de comercios y membresías; revocación explícita de privilegios en migración versionada.
- **CI / revisión en PR:** Verificación automática de la suite de integración en CI y checklist de seguridad multi-tenant en el template de Pull Request.

## Referencias

- Documentación arquitectónica y reglas de seguridad en `AGENTS.md`
- Alcance MVP del proyecto (`docs/prd/0001_alcance_mvp.md`)
