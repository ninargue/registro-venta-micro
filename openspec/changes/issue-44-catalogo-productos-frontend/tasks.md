# Tasks: issue-44-catalogo-productos-frontend

**Ticket:** #44 — US-02-T05: Vista de administración y selector de productos en frontend
**Change:** issue-44-catalogo-productos-frontend
**Orden:** topológico por capas

---

## Capa 0: Tipos y cliente API

- [ ] **T-01** Crear `frontend/src/features/catalog/types.ts` con interfaces `ProductCreate`, `ProductUpdate`, `ProductResponse`, `ProductListResponse`, `ProductListParams` — trazabilidad 1:1 con `docs/api/openapi.json` schemas `ProductCreate`, `ProductUpdate`, `ProductResponse`, `ProductListResponse`. **Origen:** nueva-declarada.

- [ ] **T-02** Crear `frontend/src/features/catalog/api.ts` con funciones:
  - `fetchProducts(params: ProductListParams): Promise<ProductListResponse>` → `GET /api/v1/catalog/products`
  - `createProduct(payload: ProductCreate): Promise<ProductResponse>` → `POST /api/v1/catalog/products`
  - `updateProduct(id: string, payload: ProductUpdate): Promise<ProductResponse>` → `PATCH /api/v1/catalog/products/{id}`
  
  Usar `apiFetch<T>` de `@/lib/api-client`. **Origen:** nueva-declarada.

- [ ] **T-03** Crear `frontend/src/features/catalog/validation.ts` con funciones de validación client-side:
  - `validateProductCreate(data): FieldErrors | null` — name no vacío, sale_price > 0
  - `validateProductUpdate(data): FieldErrors | null` — mismas reglas para los campos presentes
  
  Sin dependencias externas (igual que `auth/validation.ts`). **Origen:** nueva-declarada.

---

## Capa 1: Store Dexie para offline

- [ ] **T-04** Verificar si existe `frontend/src/lib/db.ts` (store Dexie central). Si no existe, crearlo con la clase `AppDatabase extends Dexie` y tabla `products: Table<ProductResponse>` indexada por `id`. Si existe, agregar la tabla `products` en una versión de migración Dexie incremental. **Origen:** nueva-declarada.

---

## Capa 2: Hooks TanStack Query

- [ ] **T-05** Crear `frontend/src/features/catalog/hooks/useProducts.ts`:
  - `useQuery` con `queryKey: ['catalog', 'products', params]`
  - `queryFn`: llama `fetchProducts(params)` y en éxito persiste `items` en Dexie `products`
  - Retorna `{ data, isLoading, isError, error }`
  - **Origen:** nueva-declarada.

- [ ] **T-06** Crear `frontend/src/features/catalog/hooks/useOfflineProducts.ts`:
  - Usa Dexie `useLiveQuery` para leer todos los registros de `db.products`
  - Se activa cuando `navigator.onLine === false`
  - **Origen:** nueva-declarada.

- [ ] **T-07** Crear `frontend/src/features/catalog/hooks/useCreateProduct.ts`:
  - `useMutation` que llama `createProduct(payload)`
  - En `onSuccess`: `queryClient.invalidateQueries({ queryKey: ['catalog', 'products'] })`
  - **Origen:** nueva-declarada.

- [ ] **T-08** Crear `frontend/src/features/catalog/hooks/useUpdateProduct.ts`:
  - `useMutation` que recibe `{ id, payload }` y llama `updateProduct(id, payload)`
  - En `onSuccess`: `queryClient.invalidateQueries({ queryKey: ['catalog', 'products'] })`
  - **Origen:** nueva-declarada.

---

## Capa 3: Componentes UI puros

- [ ] **T-09** Crear `frontend/src/features/catalog/components/ProductCard.tsx`:
  - Props: `product: ProductResponse`, `onEdit: (id: string) => void`
  - Muestra: nombre, precio de venta, stock
  - Botón "Editar" con `aria-label="Editar <nombre>"`, área táctil 48 px (`touch-target`)
  - Tokens: `--color-surface-*`, `--color-border-*`, `--color-text-*`, `--color-success` (stock > 0)
  - **Origen:** nueva-declarada.

- [ ] **T-10** Crear `frontend/src/features/catalog/components/ProductGrid.tsx`:
  - Props: `products: ProductResponse[]`, `onEdit: (id: string) => void`
  - Renderiza lista de `<ProductCard>`
  - Semántica: `<ul>` con `<li>` o grid con roles apropiados
  - **Origen:** nueva-declarada.

- [ ] **T-11** Crear `frontend/src/features/catalog/components/ProductSearchBar.tsx`:
  - Props: `value: string`, `onChange: (value: string) => void`, `disabled?: boolean`
  - Input con `<label>` asociado "Buscar producto", area táctil 48 px
  - Reutiliza `TextField` de `@/shared/ui/TextField`
  - **Origen:** catalogo (reutiliza TextField existente).

- [ ] **T-12** Crear `frontend/src/features/catalog/components/CatalogEmptyState.tsx`:
  - Props: `onAddProduct: () => void`
  - Texto observable "No hay productos en el catálogo" (u equivalente)
  - Botón "Agregar producto" primario
  - **Origen:** nueva-declarada.

- [ ] **T-13** Crear `frontend/src/features/catalog/components/CatalogOfflineBanner.tsx`:
  - Props: `isOffline: boolean`
  - `role="status"` o `role="alert"` con texto "Mostrando datos guardados" cuando `isOffline`
  - **Origen:** nueva-declarada.

- [ ] **T-14** Crear `frontend/src/features/catalog/components/ProductForm.tsx`:
  - Props: `mode: 'create' | 'edit'`, `initialValues?: Partial<ProductResponse>`, `onSubmit`, `onCancel`, `isLoading`, `errorMessage`, `fieldErrors`
  - Campos: Nombre (required), Precio de venta (required), Código SKU (opcional), Costo (opcional), Stock (opcional)
  - Reutiliza `TextField`, `Button`, `ErrorAlert` de `@/shared/ui`
  - Área táctil 48 px en todos los controles
  - `aria-busy` en el formulario durante envío
  - **Origen:** nueva-declarada (usa componentes catalogados).

- [ ] **T-15** Crear `frontend/src/features/catalog/pages/CatalogPage.tsx`:
  - Layout presentacional puro: cabecera de sección con heading "Catálogo de productos", `children`
  - Props: `children: ReactNode`, `onAddProduct: () => void`, `isLoading?: boolean`
  - **Origen:** nueva-declarada.

---

## Capa 4: Containers (orquestación)

- [ ] **T-16** Crear `frontend/src/features/catalog/containers/CatalogListContainer.tsx`:
  - Orquesta `useProducts`, `useOfflineProducts`; maneja debounce 300 ms en búsqueda
  - Renderiza `CatalogPage` > (`CatalogOfflineBanner`, `ProductSearchBar`, `ProductGrid` | `CatalogEmptyState` | loading | error)
  - Navega a `/catalog/new` en "Agregar", a `/catalog/:id/edit` en "Editar"
  - **Origen:** nueva-declarada.

- [ ] **T-17** Crear `frontend/src/features/catalog/containers/ProductCreateContainer.tsx`:
  - Orquesta `useCreateProduct`; maneja `validateProductCreate`, errores de red/409/422
  - Navega a `/catalog` en éxito o "Cancelar"
  - **Origen:** nueva-declarada.

- [ ] **T-18** Crear `frontend/src/features/catalog/containers/ProductEditContainer.tsx`:
  - Recibe `productId` desde `useParams()`
  - Busca el producto en la caché TanStack Query o Dexie para precargar el formulario
  - Orquesta `useUpdateProduct`; maneja errores 404, 409, 422
  - Navega a `/catalog` en éxito o "Cancelar"
  - **Origen:** nueva-declarada.

---

## Capa 5: Rutas

- [ ] **T-19** Actualizar `frontend/src/app/router.tsx`:
  - Agregar con `React.lazy`:
    - `/catalog` → `<CatalogListContainer>`
    - `/catalog/new` → `<ProductCreateContainer>`
    - `/catalog/:productId/edit` → `<ProductEditContainer>`
  - Envolver con `<Suspense fallback={...}>` en el nivel apropiado

---

## Capa 6: MSW Handlers

- [ ] **T-20** Extender `frontend/src/test/mocks/handlers.ts` con handlers por defecto para:
  - `http.get("/api/v1/catalog/products", ...)` → `ProductListResponse` fixture con 1-2 productos
  - `http.post("/api/v1/catalog/products", ...)` → `ProductResponse` fixture con `status: 201`
  - `http.patch("/api/v1/catalog/products/:product_id", ...)` → `ProductResponse` fixture actualizado

---

## Capa 7: Tests (Tests en Rojo — design-blind)

- [ ] **T-21** Crear `frontend/src/test/catalog/product-list.test.tsx` — escenarios R-01, R-02, R-03, R-04, R-14:
  - Renderiza heading "Catálogo de productos"
  - Muestra lista con nombres de productos del fixture
  - Estado de carga: `aria-busy` o `role="status"` visible
  - Estado vacío: texto observable de vacío visible
  - Búsqueda: escribir en campo "Buscar producto" dispara query con `q`
  - Error de red: `role="alert"` con mensaje de error visible

- [ ] **T-22** Crear `frontend/src/test/catalog/product-create.test.tsx` — escenarios R-05, R-06, R-07, R-08, R-09:
  - Formulario en `/catalog/new` renderiza campos requeridos
  - Envío con nombre vacío: NO invoca `POST`, campo con `aria-invalid="true"`
  - Envío con precio cero: NO invoca `POST`, mensaje de error
  - Envío válido: botón deshabilitado durante petición, navega a `/catalog` en éxito
  - Respuesta 409: mensaje `role="alert"` sobre código duplicado
  - Respuesta 422: mensaje `role="alert"` del servidor

- [ ] **T-23** Crear `frontend/src/test/catalog/product-edit.test.tsx` — escenarios R-10, R-11, R-12, R-13:
  - Formulario en `/catalog/:id/edit` pre-cargado con datos del producto
  - Envío válido: navega a `/catalog` en éxito
  - Respuesta 404: mensaje `role="alert"` de no encontrado
  - Cancelar: navega a `/catalog` sin petición

- [ ] **T-24** Crear `frontend/tests/e2e/catalog.spec.ts` — camino crítico R-15:
  - Login como dueño autenticado
  - Navega a `/catalog`
  - Activa "Agregar producto"
  - Completa nombre "Yerba Mate 1kg" y precio "3500.50"
  - Confirma formulario
  - Verifica que "Yerba Mate 1kg" aparece en la lista de `/catalog`

---

## Notas de implementación

- Mantener los tokens CSS como `var(--color-*)` sin literales `#xxx` (convención existente en todos los componentes del repo).
- El handler MSW se configura en strict mode; todo endpoint de catálogo debe tener su handler declarado en los tests de integración para no romper tests de auth existentes.
- El formulario no debe usar ninguna librería de formularios externa (patrón existente: estado controlado con `useState` + validación en `validation.ts`).
- Usar `Decimal.toString()` para mostrar precios: la API devuelve `sale_price` como `string` (`"3500.50"`); no parsear a `float`.
- El campo `cost_price` en `ProductResponse` puede llegar `null` para un usuario con rol `cashier`; el formulario de edición debe manejar este caso sin crashear.
