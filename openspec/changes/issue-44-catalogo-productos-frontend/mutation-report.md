# REPORTE DE MUTATION TESTING FRONTEND: issue-44-catalogo-productos-frontend

## 1. Veredicto de Falsabilidad

- **Estado:** `[APROBADO CON OBSERVACIONES]`
- **Tests Auditados:**
  - `frontend/src/app/features/catalog/catalog.test.tsx` (20 tests UI)
  - `frontend/src/app/features/catalog/hooks.test.ts` (9 tests de hooks)
- **Tasa de Mutantes Eliminados:** `10/14` (`71.4%`)

---

## 2. Matriz de Mutaciones Evaluadas

| ID | Categoria | Archivo Mutado | Descripcion de la Mutacion | Test que Detecto el Fallo | Resultado |
|---|---|---|---|---|---|
| M01 | FM1 | `validation.ts` | `salePrice <= 0` cambiado a `salePrice < 0` (permite precio cero) | R-06: "precio cero NO invoca POST" | Eliminado |
| M02 | FM1 | `validation.ts` | Condicion `name.length === 0` reemplazada por `false` (nunca valida nombre vacio) | R-06: "nombre vacio NO invoca POST, aria-invalid='true'" | Eliminado |
| M03 | FM3 | `useCreateProduct.ts` | Eliminado `queryClient.invalidateQueries` del `onSuccess` | hooks.test: "invalida la query ['catalog','products'] en exito" | Eliminado |
| M04 | FM3 | `useUpdateProduct.ts` | Eliminado `queryClient.invalidateQueries` del `onSuccess` | hooks.test: "invalida la query ['catalog','products'] en exito" (update) | Eliminado |
| M05 | FM3 | `useProducts.ts` | `queryKey: ["catalog", "products", params]` cambiado a `["catalog", "items", params]` | Ninguno | **VIVO** |
| M06 | FM4 | `CatalogOfflineBanner.tsx` | Eliminado `role="status"` del banner de offline | Ninguno | **VIVO** |
| M07 | FM4 | `ProductCard.tsx` | `aria-label="Editar <nombre>"` cambiado a `"Ver <nombre>"` | R-10: `getByRole("button", { name: /Editar <nombre>/i })` | Eliminado |
| M08 | FM5 | `api.ts` | Metodo HTTP de `createProduct` cambiado de `POST` a `PUT` | R-07, R-08, R-09 y hooks.test POST tests | Eliminado |
| M09 | FM5 | `api.ts` | Metodo HTTP de `updateProduct` cambiado de `PATCH` a `POST` | R-11, R-12 y hooks.test PATCH tests | Eliminado |
| M10 | FM2 | `useProducts.ts` | Eliminado `db.products.bulkPut(data.items)` (sin persistencia offline en Dexie) | Ninguno | **VIVO** |
| M11 | FM1 | `validation.ts` | Funcion `validateProductCreate` retorna siempre `null` (sin errores) | R-06: tres tests de validacion | Eliminado |
| M12 | FM3 | `ProductForm.tsx` | Eliminado `e.preventDefault()` del handler `handleSubmit` | Ninguno | **VIVO** |
| M13 | FM5 | `api.ts` | URL de `fetchProducts` cambiada a `/api/v1/catalog/items` | Multiples: hooks.test y catalog.test (7 fallos) | Eliminado |
| M14 | FM2 | `CatalogOfflineBanner.tsx` | Condicion de visibilidad invertida: `if (isOffline) return null` | R-14: "muestra aviso de modo sin conexion" | Eliminado |

---

## 3. Brechas de Falsabilidad y Accion Requerida

Se detectaron **4 mutantes vivos** que representan brechas en la cobertura de aserciones:

### Brecha B1 — M05: queryKey de `useProducts` no verificada como prerequisito de invalidacion

**Mutacion:** Cambiar `queryKey: ["catalog", "products", params]` por `["catalog", "items", params]` en `useProducts.ts`.

**Por que sobrevive:** Los tests de hooks verifican que `invalidateQueries` es llamado con `queryKey: ["catalog", "products"]`, pero no verifican que `useProducts` este registrado bajo esa misma clave. Si la clave diverge, la invalidacion nunca refresca la lista, pero los tests no lo detectan porque mockean `invalidateSpy` sin cruzarlo contra la clave real del hook.

**Accion recomendada para `frontend-qa-agent`:** En `hooks.test.ts`, agregar un test que verifique el round-trip completo: tras `useCreateProduct.mutate(...)` exitoso, `useProducts({})` debe transicionar de `isStale=true` / re-fetch observable. Alternativamente, asertar `queryClient.getQueryCache().find({ queryKey: ["catalog", "products"] })` para validar que la clave usada por `useProducts` es consistente con la invalidada por las mutations.

### Brecha B2 — M06: `role="status"` en `CatalogOfflineBanner` no validado por tests

**Mutacion:** Eliminar `role="status"` del `<div>` del banner offline.

**Por que sobrevive:** El test R-14 busca el banner por texto (`findByText(/Mostrando datos guardados|sin conexion/i)`) pero no verifica el rol semantico ARIA del elemento. Esto significa que el elemento podria degradar a un `div` anonimo sin comunicacion accesible de estado.

**Accion recomendada para `frontend-qa-agent`:** En `catalog.test.tsx` test R-14, agregar:
```ts
const banner = await screen.findByRole("status");
expect(banner).toHaveTextContent(/Mostrando datos guardados|sin conexion/i);
```
Esto garantiza que el elemento anunciante tenga el rol correcto para lectores de pantalla.

### Brecha B3 — M10: Persistencia Dexie no verificada por ningun test

**Mutacion:** Eliminar completamente `db.products.bulkPut(data.items)` de `useProducts.ts`.

**Por que sobrevive:** Ningun test verifica que los datos fetched se persistan en IndexedDB (Dexie). La suite solo valida el comportamiento de red (fetch → render), no la persistencia offline. El modo offline (R-14) tampoco sirve como proxy porque fuerza errores de red sin validar que haya datos en cache local.

**Accion recomendada para `frontend-qa-agent`:** Agregar un test en `hooks.test.ts` que mockee `db.products.bulkPut` con `vi.spyOn` y verifique que fue llamado con `data.items` tras un fetch exitoso:
```ts
const bulkPutSpy = vi.spyOn(db.products, "bulkPut").mockResolvedValue([]);
// ... renderHook y waitFor ...
expect(bulkPutSpy).toHaveBeenCalledWith(expect.arrayContaining([...]));
```

### Brecha B4 — M12: `e.preventDefault()` no verificado en JSDOM

**Mutacion:** Eliminar `e.preventDefault()` del handler `handleSubmit` en `ProductForm.tsx`.

**Por que sobrevive:** JSDOM no implementa el comportamiento de envio nativo de formularios (no recarga la pagina), por lo que la ausencia de `preventDefault()` es transparente en el entorno de tests. En un navegador real, esta mutacion causaria una recarga de pagina en cada submit.

**Accion recomendada para `frontend-qa-agent`:** Agregar un test unitario de `ProductForm` que verifique que `event.preventDefault()` es invocado:
```ts
const mockEvent = { preventDefault: vi.fn(), ... };
// fire submit and expect:
expect(mockEvent.preventDefault).toHaveBeenCalledOnce();
```
O usar `userEvent` y un spy sobre `HTMLFormElement.prototype.submit` para detectar envio nativo no prevenido.

---

## 4. Estado Final de la Suite

- **Suite tras revertir todas las mutaciones:** 73/73 tests en verde.
- **Archivos modificados durante el proceso:** todos revertidos a su estado original identico al anterior.
- **Verificacion final:** `npx vitest run` — 9 Test Files passed, 73 Tests passed.
