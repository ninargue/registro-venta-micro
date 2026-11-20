# ADR-0004: Esquema de productos con stock negativo transitorio, precisión decimal y unicidad parcial de código

- **Estado:** Aceptado
- **Fecha:** 2026-11-19
- **Autores:** Nindirí Armenta Guerrero
- **Issue / PR:** #42 / PR #57

## Contexto

El catálogo de productos debe almacenar precios de venta, costos y existencias por comercio cumpliendo dos necesidades operativas del negocio:
1. **Descuento atómico y sincronización diferida:** Las ventas realizadas en mostrador o reenviadas desde la cola sin conexión pueden descontar existencias de forma concurrente o tardía, generando temporalmente un saldo negativo cuando la reposición física aún no fue cargada en el sistema.
2. **Flexibilidad de carga e integridad histórica:** Un comercio puede registrar productos sin código o SKU asignado, pero cuando informa uno no debe repetirse dentro del mismo comercio; además, un producto discontinuado no puede eliminarse físicamente si posee ventas históricas asociadas, y las futuras entidades de detalle de venta necesitan referenciarlo preservando el aislamiento entre comercios.

## Opciones consideradas

| Opción | Ventajas | Desventajas |
|--------|----------|-------------|
| A. Imponer restricción de stock no negativo y unicidad global de código en la base de datos, con borrado físico | Impide existencias negativas desde el motor de base de datos | Bloquea el descuento atómico en ventas concurrentes o sincronización diferida, impide múltiples productos sin código y rompe la integridad referencial con el histórico de ventas |
| B. Validar precios positivos y costos no negativos en base de datos dejando el stock sin piso mínimo en el motor, usar precisión decimal exacta, unicidad condicional solo para códigos informados, clave compuesta de pertenencia al comercio y baja lógica | Garantiza exactitud monetaria sin punto flotante, soporta saldos negativos transitorios en ventas, admite productos sin código y habilita referencias compuestas aisladas por comercio | Requiere validar que el stock inicial no sea negativo en la capa de aplicación durante el alta y filtrar productos inactivos en las consultas operativas |

## Decisión

Se adopta la **Opción B**:
1. **Precisión decimal estricta:** Todos los importes monetarios (precio de venta y costo) y las existencias se almacenan con precisión decimal exacta de dos decimales, prohibiendo el uso de tipos de punto flotante.
2. **Reglas de precios frente a stock negativo transitorio:** La base de datos exige que el precio de venta sea estrictamente positivo y que el costo no sea negativo, mientras que el stock se mantiene sin restricción de piso en el motor para permitir saldos negativos transitorios durante ventas y sincronización sin conexión; la validación de stock inicial mayor o igual a cero en el alta queda bajo responsabilidad de la capa de API.
3. **Unicidad parcial de código e integridad multi-comercio:** El código de producto es opcional, exigiéndose unicidad dentro del comercio únicamente cuando el código está informado; adicionalmente, se expone una clave compuesta de comercio y producto para permitir claves foráneas compuestas en módulos dependientes.
4. **Baja lógica, auditoría y aislamiento:** Se incorpora un indicador de estado activo para desactivar productos sin perder el histórico comercial, actualización automática de la marca temporal de modificación, y aislamiento estricto por comercio mediante políticas de seguridad por fila y privilegios mínimos conforme al [ADR-0001](0001-rol-runtime-y-endurecimiento-rls.md).

## Consecuencias

- **Positivas:** Evita rechazos de sincronización sin conexión por diferencias temporales de inventario, elimina errores de redondeo binario en precios y márgenes, agiliza la carga de catálogo sin SKU obligatorio y prepara la integridad referencial multi-comercio para el módulo de ventas.
- **Negativas / trade-offs asumidos:** La base de datos por sí sola no impide registrar un stock negativo mediante inserción directa; esa regla de entrada en el alta depende de la validación de la API.
- **Riesgos y mitigaciones:** Una migración futura podría intentar restringir el stock a valores no negativos por error; se mitiga documentando esta invariante aquí y cubriendo el escenario de saldo negativo transitorio con una prueba automatizada de integración.

## Cumplimiento

- **Tests:** Suite de integración y aislamiento multi-comercio que verifica la precisión decimal exacta sin punto flotante, la unicidad condicional de códigos, la integridad referencial compuesta por comercio, el decremento de stock a valores negativos y el aislamiento efectivo bajo el rol de ejecución sin privilegios.
- **Base de datos / código:** Migración versionada reversible, modelo de dominio sincronizado con el esquema y verificación automática de ausencia de divergencias entre modelo y migraciones.
- **CI / revisión en PR:** Ejecución obligatoria de verificación de migraciones, linter, análisis de tipos y suite de pruebas en integración continua, junto con el checklist de esquema y aislamiento multi-comercio en el template de Pull Request.

## Referencias

- [ADR-0001: Rol de ejecución dedicado sin omisión de RLS y revocación de acceso directo en base de datos](0001-rol-runtime-y-endurecimiento-rls.md)
- Alcance MVP del proyecto (`docs/prd/0001_alcance_mvp.md`)
