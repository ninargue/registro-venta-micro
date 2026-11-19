# ADR-0003: Contrato uniforme de errores y resiliencia ante fallos del proveedor de identidad

- **Estado:** Aceptado
- **Fecha:** 2026-11-17
- **Autores:** Nindirí Armenta Guerrero
- **Issue / PR:** #54 / PR #52

## Contexto

Durante la revisión de seguridad de los primeros endpoints de autenticación se identificaron inconsistencias y fragilidades en el manejo de errores y consumo del servicio externo de identidad:
1. Distintos puntos de la API devolvían formatos de error incompatibles (algunos con estructura plana de código y mensaje, y otros con el envoltorio predeterminado del framework), dificultando el manejo homogéneo en el cliente.
2. Los errores de indisponibilidad, límite de tasa o tiempos de espera agotados del proveedor de autenticación se convertían en errores de credenciales inválidas o en fallos internos no controlados.
3. No existía limitación de intentos en el propio servidor antes de reenviar tráfico al proveedor externo, exponiendo la aplicación a agotamiento de cuota compartida.

## Opciones consideradas

| Opción | Ventajas | Desventajas |
|--------|----------|-------------|
| A. Manejar cada error localmente en cada ruta y abrir conexiones HTTP por petición | Menor configuración inicial en el arranque | Duplicación de formato, riesgo de respuestas inconsistentes, agotamiento de conexiones y enmascaramiento de fallos externos |
| B. Manejadores globales de excepciones con contrato único, cliente HTTP reutilizable, mapeo explícito de fallos externos y limitación de tasa en servidor | Respuestas predecibles en toda la API, reutilización de conexiones y protección frente a abuso o caídas del proveedor | Requiere mantener un limitador de tasa en memoria y disciplinar el uso del formato estándar en nuevas rutas |

## Decisión

Se adopta la **Opción B**:
1. **Contrato único de error:** Toda respuesta de error HTTP (autenticación, autorización, validación de entrada, conflicto o límite de tasa) se serializa bajo una estructura plana uniforme compuesta por código de error legible por máquina, mensaje descriptivo y detalles opcionales.
2. **Cliente HTTP compartido y tiempos de espera acotados:** La comunicación con el proveedor de identidad reutiliza un único cliente asíncrono gestionado en el ciclo de vida de la aplicación, con tiempos de espera explícitos.
3. **Mapeo fiel de errores externos:** Los rechazos por límite de tasa, errores de servidor o timeouts del proveedor externo se traducen en códigos de estado HTTP equivalentes de disponibilidad o límite de tasa, sin enmascararlos como credenciales incorrectas ni propagarlos como fallos internos.
4. **Protección preventiva y saneamiento de entradas:** El inicio de sesión aplica limitación de tasa por dirección de origen y por correo normalizado antes de consultar al proveedor externo, y las validaciones de entrada rechazan longitudes excesivas o caracteres de control nulos.

## Consecuencias

- **Positivas:** El cliente web recibe un único formato de error en todos los casos, mejora la observabilidad de caídas externas y se reduce el riesgo de denegación de servicio sobre la cuota del proveedor de identidad.
- **Negativas / trade-offs asumidos:** El limitador de tasa en memoria protege cada instancia de ejecución de forma independiente y no comparte estado entre múltiples réplicas sin un almacén distribuido.
- **Riesgos y mitigaciones:** Si el tráfico escala a múltiples réplicas concurrentes, se podrá reemplazar el almacenamiento en memoria del limitador por un backend distribuido sin alterar el contrato HTTP ni la lógica de negocio.

## Cumplimiento

- **Tests:** Pruebas unitarias y de integración que verifican el formato uniforme en errores de autenticación, validación y límite de tasa, el mapeo correcto ante respuestas `429`, `5xx` y timeouts simulados, y el rechazo de bytes nulos.
- **Base de datos / código:** Manejadores globales de excepciones registrados en la aplicación principal y validadores compartidos en los esquemas de entrada.
- **CI / revisión en PR:** Verificación automática con linter, análisis estático de tipos y suite completa de pruebas en CI.

## Referencias

- [ADR-0001: Rol de ejecución dedicado sin omisión de RLS y revocación de acceso directo en base de datos](0001-rol-runtime-y-endurecimiento-rls.md)
- [ADR-0002: Gestión de sesión mediante cookies HttpOnly y renovación sin estado](0002-sesion-httponly-y-refresh-stateless.md)
