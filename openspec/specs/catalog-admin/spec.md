# catalog-admin Specification

**Capability:** catalog-admin
**Change:** issue-44-catalogo-productos-frontend
**Contract:** contract-first — `docs/api/openapi.json`

---

## Pantallas y estados de UI

| Estado | Descripción |
|--------|-------------|
| `loading` | Spinner/skeleton visible mientras TanStack Query realiza la petición inicial. |
| `empty` | Lista sin productos (total = 0) o búsqueda sin resultados. |
| `error` | Error de red o HTTP (401, 403, 500). Mensaje accesible en `role="alert"`. |
| `offline` | Sin conectividad: se sirven productos desde la caché Dexie. Aviso de modo sin conexión. |
| `ready` | Lista de productos o formulario en estado válido listo para enviar. |

---

## Requisitos

### R-01: Lista de productos con estado de carga

**GIVEN** un usuario dueño autenticado navega a `/catalog`
**WHEN** la vista inicia la petición `GET /api/v1/catalog/products`
**THEN** se muestra un indicador de carga accesible (`aria-busy="true"` o `role="status"`)
**AND** al resolver, se presenta la lista/grilla de productos con al menos: nombre del producto, precio de venta y stock visible
**AND** el encabezado de la sección tiene nivel de heading apropiado con texto "Catálogo de productos"

---

### R-02: Lista vacía

**GIVEN** el catálogo del negocio no tiene productos registrados
**WHEN** `GET /api/v1/catalog/products` responde `200` con `{ items: [], total: 0 }`
**THEN** la vista muestra un mensaje vacío observable que indique que no hay productos
**AND** se ofrece una acción para agregar el primer producto

---

### R-03: Búsqueda reactiva por texto

**GIVEN** la lista de productos está visible en `/catalog`
**WHEN** el usuario escribe texto en el campo de búsqueda (etiquetado "Buscar producto")
**THEN** tras un debounce de ~300 ms se dispara `GET /api/v1/catalog/products?q=<texto>`
**AND** la lista se actualiza con los resultados filtrados sin recargar la página

**GIVEN** el usuario borra el texto del buscador
**WHEN** el campo queda vacío
**THEN** se dispara `GET /api/v1/catalog/products` sin parámetro `q`
**AND** se muestra el catálogo completo

---

### R-04: Error de red o servidor en listado

**GIVEN** el usuario navega a `/catalog`
**WHEN** `GET /api/v1/catalog/products` responde con un error de red o HTTP >= 400
**THEN** la vista muestra un mensaje de error observable dentro de un `role="alert"`
**AND** se ofrece una acción para reintentar la carga

---

### R-05: Acceso al formulario de alta de producto

**GIVEN** el usuario está en `/catalog`
**WHEN** activa el botón "Agregar producto" (o "Nuevo producto")
**THEN** la aplicación navega a `/catalog/new`
**AND** se presenta un formulario con los campos: Nombre (obligatorio), Precio de venta (obligatorio), Código SKU (opcional), Costo (opcional), Stock inicial (opcional)

---

### R-06: Validación client-side en formulario de alta

**GIVEN** el usuario está en `/catalog/new`
**WHEN** intenta enviar el formulario con el campo "Nombre" vacío o "Precio de venta" vacío/cero o negativo
**THEN** la aplicación NO invoca `POST /api/v1/catalog/products`
**AND** los campos inválidos reciben `aria-invalid="true"`
**AND** un mensaje de validación accesible se anuncia en un `role="alert"` o como helper text asociado al campo

---

### R-07: Alta exitosa de producto

**GIVEN** el formulario de `/catalog/new` tiene datos válidos (nombre no vacío, precio > 0)
**WHEN** el usuario confirma el envío y `POST /api/v1/catalog/products` responde `201`
**THEN** el botón de envío está deshabilitado durante la petición (`aria-busy="true"`) para evitar doble envío
**AND** al completarse, la aplicación navega a `/catalog`
**AND** el nuevo producto aparece en la lista (caché de TanStack Query invalidada)

---

### R-08: Error HTTP en alta de producto — Conflicto de SKU (409)

**GIVEN** el usuario intenta crear un producto con un código SKU ya registrado en el negocio
**WHEN** `POST /api/v1/catalog/products` responde `409 Conflict`
**THEN** el formulario permanece visible con los datos ingresados
**AND** se muestra un mensaje de error observable indicando que el código ya existe (dentro de `role="alert"`)

---

### R-09: Error HTTP en alta de producto — Validación de servidor (422)

**GIVEN** el servidor rechaza los datos del nuevo producto
**WHEN** `POST /api/v1/catalog/products` responde `422 Unprocessable Content`
**THEN** se muestra el mensaje `ErrorResponse.message` en la vista dentro de `role="alert"`

---

### R-10: Acceso al formulario de edición de producto

**GIVEN** el usuario está en `/catalog` y la lista muestra productos
**WHEN** activa la acción "Editar" sobre un producto (botón con texto o aria-label "Editar <nombre>")
**THEN** la aplicación navega a `/catalog/:productId/edit`
**AND** el formulario aparece pre-cargado con los datos actuales del producto (nombre, precio, código, costo, stock)

---

### R-11: Edición exitosa de producto

**GIVEN** el usuario modifica datos en `/catalog/:productId/edit` y los datos son válidos
**WHEN** confirma el envío y `PATCH /api/v1/catalog/products/{product_id}` responde `200`
**THEN** el botón de envío permanece deshabilitado durante la petición
**AND** al completarse, la aplicación navega a `/catalog`
**AND** el producto aparece actualizado en la lista

---

### R-12: Error HTTP en edición — Producto no encontrado (404)

**GIVEN** el usuario edita un producto que fue eliminado o no pertenece al negocio
**WHEN** `PATCH /api/v1/catalog/products/{product_id}` responde `404 Not Found`
**THEN** se muestra un mensaje observable indicando que el producto no fue encontrado
**AND** se ofrece una acción para volver al catálogo

---

### R-13: Cancelar formulario

**GIVEN** el usuario está en `/catalog/new` o `/catalog/:productId/edit`
**WHEN** activa el botón "Cancelar"
**THEN** la aplicación navega a `/catalog` sin enviar ninguna petición

---

### R-14: Modo offline — lista servida desde caché Dexie

**GIVEN** el dispositivo no tiene conectividad a la red
**WHEN** el usuario navega a `/catalog`
**THEN** la vista muestra los productos de la última sincronización guardada en IndexedDB
**AND** se muestra un aviso observable de modo sin conexión (ej. "Mostrando datos guardados")
**AND** los botones de creación y edición están deshabilitados o informan que requieren conexión

---

### R-15: Camino crítico E2E — Crear producto y verificar en lista

**GIVEN** un usuario dueño autenticado en la PWA
**WHEN** navega a "Catálogo", activa "Agregar producto", completa nombre "Yerba Mate 1kg" y precio "3500.50", confirma el formulario
**THEN** es redirigido al catálogo y el producto "Yerba Mate 1kg" aparece visible en la lista con precio "3500.50"

---

## Trazabilidad OpenAPI

| Escenario | Endpoint | Respuesta |
|-----------|----------|-----------|
| R-01, R-02, R-03, R-04, R-14 | `GET /api/v1/catalog/products` | 200 `ProductListResponse` |
| R-07 | `POST /api/v1/catalog/products` | 201 `ProductResponse` |
| R-08 | `POST /api/v1/catalog/products` | 409 `ErrorResponse` |
| R-09 | `POST /api/v1/catalog/products` | 422 `ErrorResponse` |
| R-11 | `PATCH /api/v1/catalog/products/{product_id}` | 200 `ProductResponse` |
| R-12 | `PATCH /api/v1/catalog/products/{product_id}` | 404 `ErrorResponse` |
