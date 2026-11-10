# US-02: Carga y Gestión Básica de Catálogo con Stock

**Épica:** E1-catalogo  
**Estado:** Consolidada v0.2  
**GitHub Issue:** [#41](https://github.com/ninargue/registro-venta-micro/issues/41)  

---

## 1. Descripción
**Como** dueño del micronegocio,  
**quiero** dar de alta y editar productos indicando código, nombre, precio de venta, costo y stock inicial,  
**para** tener el catálogo disponible en mostrador y permitir el control de inventario y margen.

---

## 2. Criterios de Aceptación (Given / When / Then)

### Escenario 1: Alta de un nuevo producto
- **Dado** que el dueño está autenticado en su negocio,
- **cuando** envía los datos de un nuevo producto (código opcional, nombre obligatorio, precio de venta > 0, costo >= 0, stock inicial >= 0),
- **entonces** el producto se almacena asociado al `business_id` en la tabla `products`,
- **y** los valores monetarios y de stock se guardan con precisión `Decimal` (`numeric(12,2)`).

### Escenario 2: Listado y búsqueda en catálogo
- **Dado** que existen productos registrados,
- **cuando** se consulta el catálogo o se busca por texto en el nombre o SKU,
- **entonces** el sistema retorna los productos ordenados con su precio de venta y stock actual.

### Escenario 3: Modificación de producto
- **Dado** un producto existente,
- **cuando** el dueño edita su precio de venta, costo o stock,
- **entonces** los valores se actualizan para transacciones futuras sin afectar los precios ni costos congelados en ventas pasadas.

---

## 3. Reglas de Negocio
- Los precios, costos y stock inicial son valores `Decimal`. Precios brutos sin desglose impositivo.
- Los productos eliminados o desactivados preservan la integridad referencial con el histórico de ventas.
