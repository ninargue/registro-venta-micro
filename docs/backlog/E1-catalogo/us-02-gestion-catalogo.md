# US-02: Carga y Gestión Básica de Catálogo

**Épica:** E1-catalogo  
**Estado:** Lista para refinamiento técnico  

---

## 1. Descripción
**Como** dueño del micronegocio,  
**quiero** dar de alta y editar productos indicando nombre, precio de venta, costo y stock inicial,  
**para** tener disponible los productos vendibles en el mostrador y permitir el cálculo de inventario y margen.

---

## 2. Criterios de Aceptación (Given / When / Then)

### Escenario 1: Creación de un nuevo producto
- **Dado** que el dueño está autenticado en su negocio,
- **cuando** envía los datos de un nuevo producto (código opcional, nombre obligatorio, precio de venta > 0, costo >= 0, stock inicial >= 0),
- **entonces** el producto se almacena asociado al `business_id`,
- **y** se genera el registro correspondiente en la tabla de productos con los valores monetarios en `Decimal`.

### Escenario 2: Listado y búsqueda en catálogo
- **Dado** que existen productos registrados en el negocio,
- **cuando** el usuario solicita el catálogo o busca por coincidencia de texto en el nombre,
- **entonces** el sistema retorna la lista ordenada con stock disponible y precios actuales.

### Escenario 3: Edición de precio o costo
- **Dado** un producto existente,
- **cuando** el dueño actualiza su precio de venta o costo de compra,
- **entonces** el producto se actualiza para futuras ventas, sin afectar retrospectivamente los precios ni costos históricos de ventas ya concluidas.

---

## 3. Reglas de Negocio
- Los precios y costos deben ser números positivos expresados con dos decimales (`Decimal`).
- El nombre del producto es obligatorio y no puede quedar vacío.
- Los productos eliminados o desactivados deben manejarse de forma que no rompan la integridad referencial con ventas pasadas.

---

## 4. Fuera de Alcance de esta Historia
- Carga masiva por archivo Excel/CSV en este lote.
- Imágenes de producto.
- Gestión de variantes complejas (talles, colores).
