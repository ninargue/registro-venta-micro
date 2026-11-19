# Proposal: issue-44-catalogo-productos-frontend

**Ticket:** #44 — US-02-T05: Vista de administración y selector de productos en frontend
**Issue:** [#44](https://github.com/ninargue/registro-venta-micro/issues/44)
**Capa:** frontend
**Contract mode:** contract-first
**OpenAPI path:** `docs/api/openapi.json`
**Fecha:** 2026-11-19

---

## Problema / Necesidad

El backend del catálogo (`GET /api/v1/catalog/products`, `POST /api/v1/catalog/products`, `PATCH /api/v1/catalog/products/{product_id}`) está implementado y documentado en OpenAPI, pero la PWA carece de la vista que permita al dueño del negocio visualizar, crear y editar productos desde el mostrador. Sin esta vista el catálogo existe solo en la base de datos y es inaccesible para el flujo de punto de venta.

---

## Solución Propuesta

Agregar el módulo `features/catalog` a la PWA siguiendo las convenciones establecidas del feature `auth`:

- **Rutas React Router**: `/catalog` (lista + búsqueda), `/catalog/new` (alta), `/catalog/:productId/edit` (edición).
- **Grilla táctil** de productos con nombre, precio de venta y stock. Área de pulsación mínima 48 px (ADR-0007).
- **Buscador reactivo** con debounce de 300 ms sobre el parámetro `q` de `GET /api/v1/catalog/products`.
- **Formulario único** `ProductForm` reutilizable para alta (`POST`) y edición (`PATCH`), con validación client-side antes de enviar la petición.
- **Feedback visual**: estados `loading`, `error`, `empty` y `ready` usando los tokens Tailwind `@theme` existentes.
- **Caché offline en Dexie** (IndexedDB): la lista de productos se persiste en la tabla `products` del store Dexie para ser servida en modo desconectado.
- **TanStack Query** para el estado del servidor: `useQuery` en listado, `useMutation` para alta y edición, con invalidación de caché tras escrituras exitosas.
- **MSW handlers** para los tres endpoints, siguiendo el patrón strict del `setup.ts` existente.

---

## Non-Goals

- Desactivación / borrado de productos (endpoint `DELETE` no existe en el contrato OpenAPI actual).
- Control de stock desde esta vista (movimientos de inventario pertenecen a `#46`/`#47`).
- Vista de cajero (rol `cashier`): el catálogo en modo POS para ventas es un ticket separado.
- Implementar lógica de PWA Service Worker (`workbox`): la configuración del SW es un ticket independiente de PWA bootstrap.
- Gestión de imágenes de producto.

---

## Riesgos

| Riesgo | Probabilidad | Mitigación |
|--------|-------------|------------|
| OpenAPI de `PATCH` llega después del inicio de la feature (TICKET-04b #67 en curso) | Media | El handler MSW se diseña contra el esquema `ProductUpdate` ya presente en `docs/api/openapi.json`; no hay bloqueo funcional. |
| `cost_price` visible/oculto según rol `owner`/`cashier` | Baja | El token JWT determina el rol en servidor; frontend muestra lo que responde la API (campo puede llegar `null` para `cashier` en lectura). Se omite `cost_price` del formulario inicial si el usuario no es `owner`. |
| Colisión de `code` SKU (HTTP 409) | Baja | Escenario cubierto en spec y manejado en la mutación con mensaje accesible. |
