# ADR-0006: Simulación de API en pruebas de cliente a nivel de red con MSW en modo estricto

- **Estado:** Aceptado
- **Fecha:** 2026-11-18
- **Autores:** Nindirí Armenta Guerrero
- **Issue / PR:** #56 / PR #58

## Contexto

Las pruebas unitarias y de integración de la aplicación cliente (PWA) deben validar el comportamiento de las vistas, formularios, navegación y manejo de errores ante respuestas del backend sin depender de una base de datos o un servidor FastAPI en ejecución.

Históricamente, la simulación de llamadas HTTP en entornos de prueba de JavaScript suele recurrir al espionaje o reemplazo manual de la función nativa de consulta (`fetch`), lo cual oculta discrepancias de cabeceras, ciclos de vida de peticiones, serialización de cuerpos, manejo de cookies y diferencias de semántica HTTP.

## Opciones consideradas

| Opción | Ventajas | Desventajas |
|--------|----------|-------------|
| A. Reemplazo manual de la función global de petición (`vi.fn(fetch)`) | No requiere librerías adicionales | Frágil ante cambios de rutas y cabeceras; no valida el comportamiento real de red; acopla las pruebas a la implementación interna de los clientes HTTP |
| B. Servidor HTTP local en proceso de pruebas | Pruebas de extremo a extremo reales | Alta latencia, puertos efímeros en contienda y complejidad de gestión de procesos en suites unitarias |
| C. Interceptación a nivel de red con Mock Service Worker (MSW) en modo estricto | Simula el tráfico a nivel de protocolo sin levantar sockets de red; respeta contratos HTTP estándar; permite reutilizar manejadores en desarrollo | Requiere configurar el ciclo de vida del simulador en el archivo de inicialización de la suite |

## Decisión

Se adopta la **Opción C**:
1. **Interceptación a nivel de protocolo:** Se utiliza Mock Service Worker a nivel de nodo para capturar las peticiones salientes antes de que abandonen el entorno de ejecución, simulando respuestas HTTP idénticas a las del entorno de producción.
2. **Política de fallo ante peticiones no manejadas (*Fail-Fast*):** El simulador se configura en modo estricto (`onUnhandledFrame: "error"`), haciendo fallar inmediatamente cualquier prueba que intente realizar una petición de red a una ruta no declarada o no mockeada explícitamente.
3. **Aislamiento por prueba:** Se restablece el estado de los manejadores entre cada caso de prueba para evitar fugas de simulación o contaminación cruzada de estados.

## Consecuencias

- **Positivas:** Pruebas más fieles a la realidad del navegador; detección temprana de endpoints inexistentes o mal tipados; desacoplamiento total de los componentes visuales respecto a la librería o función concreta que ejecuta las consultas.
- **Negativas / trade-offs asumidos:** Toda nueva interacción de red consumida por un componente debe contar con un manejador mock explícito en la suite o en el test correspondiente para no ser rechazada.
- **Riesgos y mitigaciones:** Riesgo de falsos positivos en suites por handlers globales mitigado mediante el restablecimiento automático tras cada ejecución (`resetHandlers`).

## Cumplimiento

- **Tests:** Prueba de verificación que valida que el servidor de simulación intercepta y responde adecuadamente ante peticiones canónicas de diagnóstico.
- **CI / revisión en PR:** Configuración centralizada en el archivo de setup de la suite de pruebas del cliente, auditada en revisiones de código.

## Referencias

- [ADR-0002](0002-sesion-httponly-y-refresh-stateless.md): Gestión de sesión mediante cookies HttpOnly y renovación sin estado.
- [ADR-0005](0005-sincronizacion-contractual-openapi-y-prevencion-drift.md): Sincronización contractual de API mediante OpenAPI estático y validación en CI.
