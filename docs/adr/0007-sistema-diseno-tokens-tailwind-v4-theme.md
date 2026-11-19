# ADR-0007: Sistema de diseño ergonómico para POS y tokens semánticos con Tailwind CSS v4 `@theme`

- **Estado:** Aceptado
- **Fecha:** 2026-11-18
- **Autores:** Nindirí Armenta Guerrero
- **Issue / PR:** #56 / PR #58

## Contexto

La aplicación cliente opera primordialmente como una terminal de punto de venta (POS) en dispositivos móviles y tabletas de mostrador de microcomercios. Este contexto impone restricciones físicas y ergonómicas severas: operación continua de pie, pantallas de diversa gama, iluminación ambiental variable y necesidad de interacción táctil rápida y precisa sin errores de pulsación.

Adicionalmente, el frontend debe mantener un tamaño de paquete mínimo, tiempo de carga casi instantáneo en condiciones de baja conectividad y evitar librerías pesadas de componentes que dificulten la personalización o aumenten el costo de mantenimiento.

## Opciones consideradas

| Opción | Ventajas | Desventajas |
|--------|----------|-------------|
| A. Librería de componentes UI prefabricados | Componentes listos para usar | Sobrecarga de dependencias, estilos difíciles de adaptar a ergonomía POS y tamaño de bundle elevado |
| B. Tailwind CSS v3 con archivo de configuración JavaScript | Ecosistema conocido y maduro | Requiere pipeline de procesamiento complejo; configuración separada en JavaScript desacoplada de las hojas de estilo |
| C. Tailwind CSS v4 con integración directa de empaquetador y directiva nativa `@theme` | Motor de compilación nativo ultra-rápido; configuración unificada dentro del archivo CSS; sin dependencias pesadas; generación determinista de utilidades | Requiere adoptar las nuevas convenciones de sintaxis CSS nativa sin depender de archivos de configuración legados |

## Decisión

Se adopta la **Opción C**:
1. **Ergonomía táctil obligatoria:** Se establece una altura y área de pulsación mínima de 48 píxeles para todos los controles interactivos de entrada, botones de acción y selecciones, minimizando errores de toque en mostrador.
2. **Tokens semánticos unificados en CSS:** Todos los colores funcionales (primarios, superficies, fondos, bordes, estados de error y éxito) y escalas tipográficas se declaran exclusivamente dentro de la directiva nativa `@theme` en la hoja de estilos principal.
3. **Alto contraste y soporte de modo oscuro:** Se adopta un esquema claro de alto contraste como predeterminado para visibilidad en mostrador con luz directa, complementado con paleta oscura para turnos nocturnos o pantallas OLED.
4. **Tipografía del sistema:** Se utiliza la pila de fuentes nativas del sistema operativo del dispositivo para evitar descargas de fuentes de red, optimizando el rendimiento de renderizado inicial (LCP) y la coherencia visual con la plataforma móvil.

## Consecuencias

- **Positivas:** Compilación de estilos en fracciones de segundo; tamaño de CSS distribuido extremadamente compacto; clases utilitarias semánticas directamente disponibles en el código de componentes; cero dependencias de bibliotecas de componentes externas.
- **Negativas / trade-offs asumidos:** Las variables de diseño deben declararse bajo las reglas formales de `@theme` para ser reconocidas por el compilador, requiriendo disciplina en el equipo para no declarar estilos sueltos en selectores no mapeados.
- **Riesgos y mitigaciones:** Riesgo de uso de selectores CSS desconectados del tema mitigado por la revisión adversarial y auditoría de hojas de estilo en el ciclo de integración.

## Cumplimiento

- **Tests:** Compilación de producción en pipeline de CI que valida la generación exitosa del paquete CSS y pruebas de renderizado de componentes.
- **CI / revisión en PR:** Verificación del cumplimiento del área táctil de 48px y uso de tokens semánticos en las especificaciones de interfaz de usuario.

## Referencias

- [ADR-0005](0005-sincronizacion-contractual-openapi-y-prevencion-drift.md): Sincronización contractual de API mediante OpenAPI estático y validación en CI.
- Especificación de diseño de autenticación y onboarding: `docs/ui/auth-onboarding-ui-spec.json`.
