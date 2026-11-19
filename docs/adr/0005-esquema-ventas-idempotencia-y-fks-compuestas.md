# ADR-0005: Esquema de ventas, idempotencia por negocio y claves foráneas compuestas

- **Estado:** Aceptado
- **Fecha:** 2026-11-19
- **Autores:** Nindirí Armenta Guerrero
- **Issue / PR:** #46 / #61

## Contexto

El sistema debe registrar ventas presenciales con múltiples medios de pago y soporte de operación sin conexión (offline-first). Cuando un dispositivo recupera conectividad, el reenvío de una venta pendiente puede repetirse por cortes de red o reintentos del cliente, por lo que la persistencia debe garantizar idempotencia estricta por negocio sin duplicar ventas, líneas ni pagos.

Además, al ser una plataforma multitenant con aislamiento impuesto por la base de datos mediante Row-Level Security (RLS), las tablas de detalle (líneas de venta y pagos) deben impedir cualquier cruce de datos entre negocios distintos, preservar los precios y costos vigentes al momento de la operación aunque el catálogo cambie o un producto intente eliminarse, y mantener una estrategia clara para validar la cuadratura entre el total vendido y los pagos recibidos.

## Opciones consideradas

### 1. Identificador de idempotencia y aislamiento multitenant en tablas hijo

| Opción | Ventajas | Desventajas |
|---|---|---|
| A. Unicidad global del identificador de cliente e integridad solo por clave primaria simple en líneas y pagos | Modelo mínimo sin columnas redundantes en tablas hijo | Permite colisiones entre negocios distintos si comparten UUID, obliga a usar subconsultas en las políticas RLS de tablas hijo y no impide a nivel de esquema referenciar una venta o producto de otro negocio |
| B. Unicidad compuesta por negocio e identificador de cliente, junto con propagación del identificador de negocio y claves foráneas compuestas en líneas y pagos | Garantiza idempotencia aislada por negocio, habilita RLS directa sin joins en todas las tablas y bloquea referencias cruzadas entre negocios en la propia base de datos | Introduce una columna de pertenencia en las tablas hijo y exige mantener claves únicas compuestas en las tablas padre |

### 2. Preservación de precios históricos y validación de cuadratura de pagos

| Opción | Ventajas | Desventajas |
|---|---|---|
| A. Calcular líneas referenciando el precio actual del producto y validar la suma de pagos mediante triggers de base de datos | Evita almacenar precios duplicados en las líneas y centraliza la cuadratura en la base de datos | Altera retroactivamente ventas pasadas al editar precios del catálogo; los triggers por fila dificultan inserciones parciales de venta y pagos dentro de una misma transacción |
| B. Congelar precio y costo unitario en cada línea, restringir el borrado de productos con ventas y validar la cuadratura de pagos en la capa de servicio transaccional | Mantiene el historial contable y de márgenes intacto en tercera forma normal, protege la integridad histórica y permite transacciones atómicas ordenadas desde el servicio | Requiere que la lógica de aplicación copie los precios del catálogo y verifique que los pagos cubran el total antes de confirmar la transacción |

## Decisión

Se adopta la **Opción B** en ambos ejes de diseño:

1. **Idempotencia acotada por negocio:** Toda venta requiere un identificador generado en el cliente cuya unicidad se exige de forma compuesta junto al negocio propietario, permitiendo reintentos idempotentes sin riesgo de interferencia entre distintos negocios.
2. **Aislamiento directo y claves foráneas compuestas:** Las líneas de venta y los pagos incorporan el identificador de negocio y se vinculan mediante claves foráneas compuestas tanto hacia la venta como hacia el producto, asegurando que ninguna línea o pago pueda asociarse a recursos de otro negocio y que las políticas RLS evalúen el contexto de sesión directamente sobre cada fila.
3. **Congelamiento histórico en líneas de venta:** Cada línea almacena el precio y costo unitario vigentes en el momento de la venta como instantánea contable (en tercera forma normal, sin persistir subtotales derivados), y la relación hacia el producto impide su eliminación física cuando ya participó en ventas.
4. **Precisión uniforme y validación transaccional de pagos:** Las cantidades vendidas adoptan la misma precisión decimal fija que el inventario de productos, mientras que la verificación de suma de pagos frente al total de la venta permanece en la capa de servicio transaccional para no acoplar el orden de inserción de líneas y pagos a triggers de base de datos.

## Consecuencias

- **Positivas:**
  - Los reenvíos offline repetidos son seguros e idempotentes por negocio.
  - Todas las tablas operativas de ventas aplican RLS forzada de forma uniforme y eficiente sin subconsultas entre tablas.
  - El historial de ventas y márgenes permanece inmutable frente a cambios de precio o intentos de eliminación de productos.
- **Negativas / trade-offs asumidos:**
  - Mayor cantidad de restricciones compuestas e índices en el esquema inicial.
  - La consistencia entre el total de la venta y la suma de sus pagos depende de la validación atómica en la capa de servicio transaccional.
- **Riesgos y mitigaciones:**
  - *Riesgo:* inserción directa sin pasar por el servicio podría grabar pagos que no igualen el total. *Mitigación:* el acceso en runtime está restringido a la aplicación y la validación de cuadratura es obligatoria en el servicio transaccional de ventas.

## Cumplimiento

- **Tests:** Suite de integración de base de datos que verifica unicidad por negocio e idempotencia ante reintentos, bloqueo de referencias cruzadas entre negocios, rechazo de eliminación de productos con ventas, congelamiento de precios y aislamiento RLS completo. Validación adicional mediante pruebas de mutación y falsabilidad.
- **Base de datos / código:** Migraciones versionadas con RLS activada y forzada para las cuatro operaciones, privilegios de mínimo acceso para el rol de aplicación y sincronía verificada entre el esquema de base de datos y los modelos de persistencia.
- **CI / revisión en PR:** Verificación automática de migraciones, tipado, linter y suite de tests en el flujo de integración continua y en el checklist oficial de Pull Request.

## Referencias

- [ADR-0001: Rol de runtime sin privilegios BYPASSRLS y endurecimiento RLS](0001-rol-runtime-y-endurecimiento-rls.md)
- [ADR-0004: Esquema de productos, stock negativo transitorio y unicidad parcial de código](0004-esquema-productos-stock-negativo-y-unicidad-parcial.md)
- Especificación canónica: `openspec/specs/sales-schema-and-rls/spec.md`
