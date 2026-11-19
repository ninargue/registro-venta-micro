# Verification Report: issue-44-catalogo-productos-frontend

**Ticket:** #44 — US-02-T05: Vista de administración y selector de productos en frontend
**Rama:** `feature/44-catalogo-productos-frontend`
**Fase:** B (Post-Auditoría)
**Fecha:** 2026-11-19
**Veredicto:** APROBADO CON OBSERVACIONES

---

## Resultado de la suite de tests

```
Test Files  9 passed (9)
Tests       73 passed (73)
Duration    13.47s
```

Todos los tests están en **VERDE**. No hay tests en rojo ni saltados.

---

## 1. Completeness — Cobertura de requisitos (R-01 a R-15)

| Escenario | Descripción | Tests unitarios/integración | Test E2E | Resultado |
|-----------|-------------|----------------------------|----------|-----------|
| R-01 | Lista con estado de carga | `catalog.test.tsx` (2 tests: loading indicator + heading/datos) + `hooks.test.ts` (isLoading) | — | CUBIERTO |
| R-02 | Lista vacía | `catalog.test.tsx` (1 test: empty state + acción agregar) | — | CUBIERTO |
| R-03 | Búsqueda reactiva por texto | `catalog.test.tsx` (2 tests: q= tras debounce + clear) + `hooks.test.ts` (q param forwarding, omisión q vacío) | — | CUBIERTO |
| R-04 | Error de red o servidor | `catalog.test.tsx` (2 tests: network error + HTTP 500) + `hooks.test.ts` (isError) | — | CUBIERTO |
| R-05 | Acceso formulario de alta | `catalog.test.tsx` (1 test: navega /catalog/new + todos los campos) | — | CUBIERTO |
| R-06 | Validación client-side en alta | `catalog.test.tsx` (3 tests: nombre vacío, precio=0, precio negativo) | — | CUBIERTO |
| R-07 | Alta exitosa | `catalog.test.tsx` (1 test: aria-busy + navega /catalog) + `hooks.test.ts` (POST + cache invalidation) | — | CUBIERTO |
| R-08 | Error 409 (SKU duplicado) | `catalog.test.tsx` (1 test: form visible + alert) + `hooks.test.ts` (isError) | — | CUBIERTO |
| R-09 | Error 422 (validación servidor) | `catalog.test.tsx` (1 test: mensaje servidor en alert) + `hooks.test.ts` (isError) | — | CUBIERTO |
| R-10 | Acceso formulario de edición | `catalog.test.tsx` (1 test: navega /catalog/:id/edit + form pre-cargado) | — | CUBIERTO |
| R-11 | Edición exitosa | `catalog.test.tsx` (1 test: aria-busy + navega /catalog) + `hooks.test.ts` (PATCH + cache invalidation) | — | CUBIERTO |
| R-12 | Error 404 (producto no encontrado) | `catalog.test.tsx` (1 test: alert + acción volver) + `hooks.test.ts` (isError) | — | CUBIERTO |
| R-13 | Cancelar formulario | `catalog.test.tsx` (2 tests: cancel desde /new y desde /:id/edit) | — | CUBIERTO |
| R-14 | Modo offline — caché Dexie | `catalog.test.tsx` (1 test: banner offline + botón deshabilitado) | — | CUBIERTO |
| R-15 | Camino crítico E2E | — | `frontend/tests/e2e/catalog.spec.ts` (login → /catalog → crear → verificar) | CUBIERTO |

**Resultado: 15/15 escenarios cubiertos.**

---

## 2. Correctness — Drift check

### 2.1 Componentes implementados vs. árbol en design.md

| Artefacto especificado | Ruta implementada | Estado |
|------------------------|-------------------|--------|
| `containers/CatalogListContainer.tsx` | `frontend/src/features/catalog/containers/CatalogListContainer.tsx` | PRESENTE |
| `containers/ProductCreateContainer.tsx` | `frontend/src/features/catalog/containers/ProductCreateContainer.tsx` | PRESENTE |
| `containers/ProductEditContainer.tsx` | `frontend/src/features/catalog/containers/ProductEditContainer.tsx` | PRESENTE |
| `components/ProductSearchBar.tsx` | `frontend/src/features/catalog/components/ProductSearchBar.tsx` | PRESENTE |
| `components/ProductGrid.tsx` | `frontend/src/features/catalog/components/ProductGrid.tsx` | PRESENTE |
| `components/ProductCard.tsx` | `frontend/src/features/catalog/components/ProductCard.tsx` | PRESENTE |
| `components/ProductForm.tsx` | `frontend/src/features/catalog/components/ProductForm.tsx` | PRESENTE |
| `components/CatalogEmptyState.tsx` | `frontend/src/features/catalog/components/CatalogEmptyState.tsx` | PRESENTE |
| `components/CatalogOfflineBanner.tsx` | `frontend/src/features/catalog/components/CatalogOfflineBanner.tsx` | PRESENTE |
| `pages/CatalogPage.tsx` | `frontend/src/features/catalog/pages/CatalogPage.tsx` | PRESENTE |
| `hooks/useProducts.ts` | `frontend/src/features/catalog/hooks/useProducts.ts` | PRESENTE |
| `hooks/useCreateProduct.ts` | `frontend/src/features/catalog/hooks/useCreateProduct.ts` | PRESENTE |
| `hooks/useUpdateProduct.ts` | `frontend/src/features/catalog/hooks/useUpdateProduct.ts` | PRESENTE |
| `hooks/useOfflineProducts.ts` | `frontend/src/features/catalog/hooks/useOfflineProducts.ts` | PRESENTE |
| `api.ts`, `types.ts`, `validation.ts` | mismas rutas | PRESENTES |

**Árbol de componentes: CONFORME con design.md.**

### 2.2 Rutas React Router

| Ruta especificada | Componente | Lazy | Suspense fallback | Estado |
|-------------------|-----------|------|-------------------|--------|
| `/catalog` | `CatalogListContainer` | React.lazy | `role="status"` | CONFORME |
| `/catalog/new` | `ProductCreateContainer` | React.lazy | `role="status"` | CONFORME |
| `/catalog/:productId/edit` | `ProductEditContainer` | React.lazy | `role="status"` | CONFORME |

### 2.3 Query keys y cache invalidation

- `useProducts` usa `queryKey: ["catalog", "products", params]` — CONFORME.
- `useCreateProduct.onSuccess` invalida `{ queryKey: ["catalog", "products"] }` — CONFORME.
- `useUpdateProduct.onSuccess` invalida `{ queryKey: ["catalog", "products"] }` — CONFORME.

### 2.4 Validación client-side

`validateProductCreate` rechaza: nombre vacío/longitud > 150, `sale_price` ausente o <= 0 — CONFORME con R-06.
`validateProductUpdate` valida los mismos campos si están presentes — CONFORME.

### 2.5 Comportamiento offline (R-14)

- `CatalogListContainer` inicializa `isOffline` con `!navigator.onLine` y suscribe los eventos `online`/`offline`. CONFORME.
- `CatalogOfflineBanner` renderiza el texto "Mostrando datos guardados — sin conexión a Internet" con `role="status"` y `aria-live="polite"`. CONFORME con la aserción del test (`/Mostrando datos guardados|sin conexión/i`).
- Botón "Agregar producto" en `CatalogPage`: `disabled={isLoading || isOffline}`. CONFORME.
- Botones "Editar" en `ProductCard`: `disabled={isOffline}` via prop en `ProductGrid`. CONFORME.

---

## 3. Coherence — Hallazgos y observaciones

### OBS-01 (BAJA) — Drift menor en `ProductCreate.cost_price` y `ProductCreate.stock` vs. OpenAPI

**Ubicación:** `frontend/src/features/catalog/types.ts` vs. `docs/api/openapi.json`

El esquema OpenAPI de `ProductCreate` define `cost_price` como `number | string` (sin `null`) y `stock` como `number | string` (sin `null`). La interfaz TypeScript en `types.ts` los declara como `string | number | null`, añadiendo `null` que el contrato no acepta.

```
OpenAPI ProductCreate.cost_price: anyOf[number, string]  — sin null
TypeScript ProductCreate.cost_price: string | number | null  — con null
```

Impacto: el compilador no impedirá pasar `null` para estos campos en alta de producto. En tiempo de ejecución el servidor rechazaría el payload. No bloquea el flujo actual porque el formulario nunca envía `null` explícito para estos campos (envía `undefined` cuando están vacíos). La divergencia es tipológica, no funcional.

Triaje: **Integrador** — revisar si el contrato debería permitir `null` para estos campos (alineando OpenAPI) o ajustar types.ts para eliminar `null` en `ProductCreate`.

### OBS-02 (BAJA) — `useOfflineProducts` usa `useEffect + useState` en lugar de `useLiveQuery`

**Ubicación:** `frontend/src/features/catalog/hooks/useOfflineProducts.ts`

La tarea T-06 en `tasks.md` y el `design.md` especifican que `useOfflineProducts` debe usar `useLiveQuery` de Dexie para reactividad en tiempo real sobre la tabla IndexedDB. La implementación usa `useEffect + useState` con una carga única al montar.

Consecuencia práctica: si otra pestaña del navegador modifica la tabla `products` en IndexedDB mientras el componente está montado, la vista no se actualizará reactivamente. Para el flujo actual (modo offline solo lectura, sin edición simultánea) no impacta al usuario. Sin embargo, se desvía de la especificación de diseño.

Triaje: **Integrador** — evaluar migrar a `useLiveQuery` para alinear con la spec y preparar el módulo para futuros escenarios de sync en background.

### OBS-03 (BAJA) — Ubicación de los archivos de test difiere de `tests_dir` en design.md

**Ubicación:** `frontend/src/app/features/catalog/catalog.test.tsx`, `frontend/src/app/features/catalog/hooks.test.ts`

Design.md especifica `tests_dir: "frontend/src/test"` y `test_pattern: "frontend/src/test/{domain}/*.test.tsx"`. Los tests del catálogo están co-ubicados con el código de feature en `src/app/features/catalog/`, no en `src/test/catalog/`.

Adicionalmente, en `tasks.md` las tareas T-21, T-22 y T-23 aparecen marcadas como `[ ]` (incompletas), cuando los tests correspondientes existen y pasan. Las rutas que describen los tasks (`src/test/catalog/product-list.test.tsx`, etc.) no coinciden con donde se crearon efectivamente los archivos.

Impacto: los tests pasan y cubren todos los escenarios requeridos. El problema es de trazabilidad de tareas y consistencia de convención de directorio. No bloquea el merge.

Triaje: **Tester** — marcar T-21, T-22, T-23 como `[x]` en `tasks.md` con nota de ruta real, o mover los archivos a `src/test/catalog/` para ajustar la convención de proyecto.

### OBS-04 (INFORMATIVO) — `ProductEditContainer` carga el producto desde la lista, no desde endpoint individual

La especificación de `ProductEditContainer` en `tasks.md` dice "Busca el producto en la caché TanStack Query o Dexie". La implementación llama `useProducts({})` para obtener la lista completa y luego hace `find` por ID. No existe un endpoint `GET /api/v1/catalog/products/{product_id}` en el contrato OpenAPI, por lo que esta estrategia es la correcta dado el contrato actual.

No es una observación de corrección sino de contexto: si en el futuro se agrega el endpoint individual, se deberá actualizar `ProductEditContainer` para usar un hook dedicado.

---

## 4. Accesibilidad (ARIA)

| Control | ARIA/semántica | Resultado |
|---------|---------------|-----------|
| Spinner de carga | `role="status"` + `aria-label` | CONFORME |
| Mensajes de error | `ErrorAlert` con `role="alert"` | CONFORME |
| Banner offline | `role="status"` + `aria-live="polite"` | CONFORME |
| Campo nombre con error | `aria-invalid="true"` + helperText | CONFORME |
| Botón "Editar" por producto | `aria-label="Editar {nombre}"` | CONFORME |
| Botón "Agregar producto" | `aria-label="Agregar producto"` | CONFORME |
| Botón submit durante mutación | `aria-busy="true"` + `disabled` | CONFORME |
| Formulario durante envío | `aria-busy={isLoading}` en `<form>` | CONFORME |
| Campos requeridos | `required` + asterisco `aria-hidden` | CONFORME |

### Ergonomía táctil (ADR-0007)

- `.touch-target { min-height: 48px; min-width: 48px; }` definida en `frontend/src/index.css`.
- `Button` y `TextField` aplican la clase `touch-target`. CONFORME.

---

## 5. Cobertura de trazabilidad OpenAPI

| Endpoint | Método | Código | Cubierto en tests |
|----------|--------|--------|-------------------|
| `/api/v1/catalog/products` | GET 200 | `ProductListResponse` | hooks.test.ts + catalog.test.tsx R-01/02/03 |
| `/api/v1/catalog/products` | GET error | red / 500 | catalog.test.tsx R-04 |
| `/api/v1/catalog/products` | POST 201 | `ProductResponse` | hooks.test.ts + catalog.test.tsx R-07 |
| `/api/v1/catalog/products` | POST 409 | `ErrorResponse` | hooks.test.ts + catalog.test.tsx R-08 |
| `/api/v1/catalog/products` | POST 422 | `ErrorResponse` | hooks.test.ts + catalog.test.tsx R-09 |
| `/api/v1/catalog/products/{id}` | PATCH 200 | `ProductResponse` | hooks.test.ts + catalog.test.tsx R-11 |
| `/api/v1/catalog/products/{id}` | PATCH 404 | `ErrorResponse` | hooks.test.ts + catalog.test.tsx R-12 |

**Cobertura de trazabilidad: 7/7 (completa).**

---

## 6. Resumen ejecutivo

| Dimensión | Resultado |
|-----------|-----------|
| Tests en verde | 73/73 |
| Completeness (tasks.md) | 15/15 escenarios cubiertos; T-21/T-22/T-23 marcados `[ ]` por inconsistencia de ruta (OBS-03) |
| Correctness (R-01 a R-15) | 15/15 Given/When/Then verificados en VERDE |
| Coherence — drift vs. design.md | 2 divergencias no bloqueantes (OBS-01, OBS-02) |
| Coherence — drift vs. openapi.json | 1 divergencia tipológica menor (OBS-01) |
| Accesibilidad ARIA | Conforme |
| Ergonomía táctil 48px | Conforme |
| Lazy loading / bundle | Conforme (React.lazy en router.tsx) |

**Veredicto: APROBADO CON OBSERVACIONES**

Las 4 observaciones son de baja severidad y no bloquean el merge. Se recomienda resolverlas antes del siguiente ciclo de auditoría para mantener la consistencia entre el contrato, el diseño y la implementación.
