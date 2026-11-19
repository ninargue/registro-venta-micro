# ADR-0005: Sincronización contractual de API mediante OpenAPI estático y validación en CI

- **Estado:** Aceptado
- **Fecha:** 2026-11-18
- **Autores:** Nindirí Armenta Guerrero
- **Issue / PR:** #56 / PR #58

## Contexto

El desarrollo desacoplado entre el servicio de backend y la aplicación cliente (PWA) requiere un contrato formal, unívoco y versionado de las operaciones de la API REST. Sin una especificación accesible en el repositorio, las pruebas de integración del cliente, los simuladores de red y la tipificación dependen de consultar un entorno de ejecución levantado en vivo o de acuerdos informales propensos a desincronización (*API drift*).

Al mismo tiempo, intentar forzar la regeneración y el agregado automático del esquema en los hooks de confirmación de cambios en el entorno de desarrollo local puede interferir con operaciones parciales de preparación de commits y provocar condiciones de carrera en el control de versiones.

## Opciones consideradas

| Opción | Ventajas | Desventajas |
|--------|----------|-------------|
| A. Consulta dinámica a la instancia de desarrollo en ejecución | No requiere persistir artefactos intermedios en el repositorio | Obliga a mantener el servidor backend corriendo para cualquier tarea o prueba en el frontend; no auditable en revisiones de código |
| B. Exportación estática automatizada en pre-commit forzando agregado de archivos al índice de Git | Mantiene el archivo sincronizado automáticamente antes de confirmar cambios locales | Rompe commits interactivos parciales, contamina argumentos de herramientas de formateo y viola las directrices de herramientas de hooks locales |
| C. Exportación estática explícita con verificación determinista de sincronización en integración continua (CI) | Contrato versionado en repositorio; no interfiere con commits parciales; garantiza que ningún cambio a la API se integre sin su especificación actualizada | Requiere ejecutar el comando de exportación al modificar rutas y esquemas del backend |

## Decisión

Se adopta la **Opción C**:
1. **Artefacto contractual canónico:** Se mantiene una especificación OpenAPI en formato JSON versionada en la documentación del repositorio, reflejando fielmente el contrato público de todas las rutas y modelos de datos.
2. **Generación determinista:** Se dispone de una rutina de exportación estática que extrae el esquema OpenAPI directamente de la aplicación de backend sin requerir levantar servicios de red.
3. **Verificación estricta en integración continua:** El pipeline de integración continua del backend ejecuta la rutina de exportación y verifica que no existan discrepancias entre el código y el esquema persistido. Cualquier divergencia no confirmada bloquea la integración.
4. **Prohibición de agregado colateral en hooks locales:** Las tareas automáticas de preparación de commits se limitan a analizar y formatear los archivos preparados, sin forzar agregados de archivos no relacionados al índice de cambios.

## Consecuencias

- **Positivas:** El cliente y las pruebas disponen de una fuente de verdad fija y trazable; los cambios de contrato son visibles y auditables en los pull requests; se previenen desincronizaciones silenciosas entre backend y frontend.
- **Negativas / trade-offs asumidos:** Los desarrolladores que modifiquen esquemas o controladores en el backend deben recordar exportar el archivo OpenAPI o apoyarse en la advertencia determinista que emite el pipeline de CI.
- **Riesgos y mitigaciones:** Riesgo de commits con contrato desfasado mitigado por la comprobación bloqueante en CI (`git diff --exit-code`).

## Cumplimiento

- **Tests:** Pruebas unitarias que verifican la validez sintáctica del esquema generado y la presencia de las operaciones críticas de la API.
- **CI / revisión en PR:** Paso específico en el flujo de integración continua que regenera el archivo y verifica la ausencia de diferencias respecto a la versión en control de cambios.

## Referencias

- [ADR-0003](0003-contrato-uniforme-errores-y-resiliencia-auth.md): Contrato uniforme de respuestas de error y resiliencia en autenticación.
- [ADR-0006](0006-simulacion-api-frontend-msw-red.md): Simulación de API en pruebas de cliente a nivel de red con MSW en modo estricto.
