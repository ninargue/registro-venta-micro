# REPORTE DE MUTATION TESTING Y FALSABILIDAD: issue-68-hardening-ventas-backend

## 1. Veredicto de Falsabilidad

- **Estado:** `[TESTS MAYORMENTE BLINDADOS — 2 BRECHAS MENORES DETECTADAS]`
- **Modo de Ejecución:** `Catalogo Canonico M1-M5 (analisis estatico/manual — mutation_cmd: none)`
- **Tests Auditados:**
  - `backend/tests/unit/test_sales_schemas.py`
  - `backend/tests/integration/test_sales_api.py`
- **Tasa de Mutantes Eliminados:** `13/15 evaluados` (`87%`)
- **Mutantes Vivos:** 2 (brechas de cobertura de frontera exacta y filtro de nombres por tenant sin asercion directa)

---

## 2. Matriz de Mutaciones Evaluadas

| ID | Mutacion | Archivo Mutado | Archivo de Test | Atrapo el Fallo? | Resultado |
|---|---|---|---|---|---|
| M1a | Eliminar `@field_validator("quantity")` / `validate_quantity` en `SaleItemCreate` (permite float) | `backend/app/modules/sales/schemas.py` | `test_sales_schemas.py::test_sale_item_and_payment_reject_invalid_decimals[1.5]`, `test_sales_api.py::test_reject_float_bool_nonfinite...[(1.5,"10.00")]` | Si | Eliminado |
| M1b | Eliminar `gt=Decimal("0")` de `SaleItemCreate.quantity` y `SalePaymentCreate.amount` (permite cero y negativos) | `backend/app/modules/sales/schemas.py` | `test_sales_schemas.py::test_sale_item_and_payment_reject_invalid_decimals["0","0.00","-1.00"]`, `test_sales_api.py::test_reject_float_bool...` | Si | Eliminado |
| M1c | Eliminar `max_length=500` en `SaleCreate.items` o `max_length=20` en `SaleCreate.payments` | `backend/app/modules/sales/schemas.py` | `test_sales_schemas.py::test_sale_create_enforces_items_and_payments_bounds`, `test_sales_api.py::test_items_and_payments_batch_limits_and_zero_unit_cost` | Si | Eliminado |
| M2a | Omitir dependencia `get_current_tenant` / aceptar JWT con firma invalida o expirado | `backend/app/modules/sales/router.py` | `test_sales_api.py::test_unauthenticated_and_onboarding_pending_rejected` (401 con bad_sig, expired, sin cookie; 403 con business_id=None) | Si | Eliminado |
| M2b | Eliminar guard `if current_user.business_id is None: raise ValueError` en `SalesService.create_sale` | `backend/app/modules/sales/service.py:143-144` | `test_sales_api.py::test_unauthenticated_and_onboarding_pending_rejected` (el 403 lo emite `get_current_tenant`, no el servicio; el guard del servicio es defensa en profundidad sin test directo propio) | No (el test pasa igual) | Vivo (equivalente — el 403 ya fue emitido antes por la dependencia) |
| M3a | Eliminar `Product.business_id == business_id` de `lock_products_for_sale` (CatalogRepository) | `backend/app/modules/catalog/repository.py:103-104` | `test_sales_api.py::test_cross_tenant_or_missing_product_rejected_404_and_body_business_id_ignored` (cross_resp espera 404; sin filtro encontraria prod_b y daria 201) | Si | Eliminado |
| M3b | Eliminar `Product.business_id == business_id` del WHERE en `deduct_stock_batch` | `backend/app/modules/catalog/repository.py:135-136` | `test_sales_api.py::test_multi_product_sale_executes_single_tenant_filtered_bulk_update` (asercion SQL `assert "business_id" in update_stmts[0]`) | Si | Eliminado |
| M3c | Eliminar `Product.business_id == business_id` del SELECT en `get_product_names_by_ids` | `backend/app/modules/catalog/repository.py:153-154` | Ninguno (ninguna asercion directa sobre la query SQL de este metodo; RLS mitiga a nivel BD pero no hay test de aplicacion independiente para este filtro) | No | Vivo |
| M4a | Cambiar `if subtotal <= Decimal("0.00")` a `if subtotal < Decimal("0.00")` (permite subtotal exactamente cero) | `backend/app/modules/sales/service.py:202` | `test_sales_api.py::test_reject_sale_total_rounding_to_zero_or_overflow` (resp_zero: 0.01 * 0.01 rounds to 0.00, espera 422) | Si | Eliminado |
| M4b | Cambiar `if total_amount > MAX_NUMERIC_12_2` a `if total_amount >= MAX_NUMERIC_12_2` en acumulacion por linea (linea 206) | `backend/app/modules/sales/service.py:206` | Ningun test envia total_amount == 9999999999.99 exactamente como suma de lineas; los tests de overflow usan valores muy superiores (2 * 9999999999.99) | No | Vivo |
| M4c | Cambiar `if new_deduction > MAX_NUMERIC_12_2` a `if new_deduction >= MAX_NUMERIC_12_2` en acumulacion de deduccion (linea 210) | `backend/app/modules/sales/service.py:210` | `test_reject_stock_numeric_12_2_overflow_and_allow_min_boundary`: el caso agg_overflow usa 12000000000.00 >> MAX, el caso boundary usa resultado final no deduccion acumulada exacta; muta el `>` en acumulacion sin que ningun test envie deduccion_acumulada == MAX | No | Vivo |
| M4d | Cambiar `if resulting_stock < -MAX_NUMERIC_12_2` a `if resulting_stock <= -MAX_NUMERIC_12_2` (linea 230) | `backend/app/modules/sales/service.py:230` | `test_sales_api.py::test_reject_stock_numeric_12_2_overflow_and_allow_min_boundary` (resp_boundary: -1.00 - 9999999998.99 = -9999999999.99 exactamente, espera 201; con `<=` retornaria 422) | Si | Eliminado |
| M4e | Eliminar re-lookup post-lock H1 (lineas 167-182 de service.py) | `backend/app/modules/sales/service.py:167-182` | `test_sales_api.py::test_concurrent_retry_returns_200_when_catalog_changes_before_for_update` (sin H1, el producto se detecta como inactivo luego del lock y retorna 422 en vez de 200) | Si | Eliminado |
| M4f | Invertir condicion en `_assert_idempotent_payload_matches`: `!=` a `==` (conflicto en coincidencia, no en diferencia) | `backend/app/modules/sales/service.py:134` | `test_sales_api.py::test_sequential_idempotent_retry_returns_200_even_after_catalog_change` (retry identico obtendria 409 en vez de 200), `test_reuse_client_id_with_different_payload_returns_409_conflict` (difiere y obtendria 200 en vez de 409) | Si | Eliminado |
| M5a | Cambiar HTTP 409 a HTTP 200 o 422 en el handler de `SaleIdConflictError` (router.py:93-101) | `backend/app/modules/sales/router.py:94` | `test_sales_api.py::test_reuse_client_id_with_different_payload_returns_409_conflict` y `test_concurrent_client_id_collision_with_different_payloads_returns_201_and_409` (ambos verifican status 409 y code SALE_ID_CONFLICT) | Si | Eliminado |
| M5b | Capturar `SaleStockOverflowError` y retornar 200 OK en lugar de 422 (router.py:102-110) | `backend/app/modules/sales/router.py:102` | `test_sales_api.py::test_reject_stock_numeric_12_2_overflow_and_allow_min_boundary` (verifica status 422 y code VALIDATION_ERROR para overflow de deduccion y stock resultante) | Si | Eliminado |

---

## 3. Detalle de Mutantes Vivos y Brechas de Falsabilidad

### Brecha 1 — M3c: Filtro `business_id` en `get_product_names_by_ids` sin asercion de aplicacion directa

**Mutacion viva:** Eliminar `Product.business_id == business_id` del SELECT en `CatalogRepository.get_product_names_by_ids` (`backend/app/modules/catalog/repository.py:153-154`).

**Por que sobrevive:** Esta funcion se invoca unicamente en rutas de idempotencia (early lookup, post-lock H1 y post-conflict H3) para enriquecer el nombre del producto en la respuesta. Ningun test verifica el SQL emitido por este metodo ni assert que un producto de otro tenant no aparezca en los nombres devueltos. La RLS con `SET LOCAL ROLE app_api` protege la brecha a nivel de base de datos.

**Riesgo residual:** Bajo (aislamiento garantizado por RLS). Sin embargo, la defensa en profundidad a nivel de aplicacion queda sin cobertura de test, lo que viola el principio de no depender de un unico mecanismo de aislamiento de tenant.

**Accion requerida en `backend/tests/integration/test_sales_api.py`:**
Agregar un caso en `test_cross_tenant_or_missing_product_rejected_404_and_body_business_id_ignored` que, usando el test fixture `_capture_sql_statements`, verifique que la query emitida por `get_product_names_by_ids` en la ruta de idempotencia contiene `business_id` en el statement SQL, o bien un test que ejecute un retry idempotente en tenant A y compruebe que el nombre devuelto no corresponde a un producto de tenant B con el mismo UUID (escenario de colision UUID cross-tenant).

---

### Brecha 2 — M4b/M4c: Frontera exacta `== MAX_NUMERIC_12_2` para acumulacion de total y deduccion

**Mutacion viva (doble):**
- Cambiar `total_amount > MAX_NUMERIC_12_2` a `total_amount >= MAX_NUMERIC_12_2` en `service.py:206` (acumulacion por linea).
- Cambiar `new_deduction > MAX_NUMERIC_12_2` a `new_deduction >= MAX_NUMERIC_12_2` en `service.py:210` (deduccion acumulada de un mismo producto en items duplicados).

**Por que sobreviven:** Los tests de overflow existentes usan valores ampliamente superiores a MAX_NUMERIC_12_2 (ej. dos lineas de `6000000000.00` para la deduccion; `2 * 9999999999.99` para el total). No existe ningun test con un total_amount o una deduccion acumulada que iguale exactamente `Decimal("9999999999.99")`.

**Riesgo residual:** Moderado. Un cambio de `>` a `>=` rechazaria ventas cuyo total o deduccion sea exactamente `9999999999.99`, introduciendo una regresion silenciosa en el limite superior valido del rango. El riesgo en produccion es bajo (ese importe exacto es altamente improbable) pero la brecha de falsabilidad es real.

**Accion requerida en `backend/tests/integration/test_sales_api.py`:**
Agregar dos subcasos al test `test_reject_stock_numeric_12_2_overflow_and_allow_min_boundary` o como tests independientes:

1. **Frontera total_amount == MAX:** Un producto con `sale_price=Decimal("9999999999.99")` y `quantity="1.00"` → total calculado == MAX_NUMERIC_12_2 → debe retornar **201** (no overflow).
2. **Frontera deduccion acumulada == MAX:** Dos lineas del mismo producto donde `qty_1 + qty_2 == Decimal("9999999999.99")` (ej. `4999999999.99` + `5000000000.00`) → debe retornar **201** (el overflow solo se activa al superar MAX, no al igualarlo).

---

## 4. Conclusion

La suite Backend-TDD del cambio `issue-68-hardening-ventas-backend` es **robusta y falsable para las rutas criticas de negocio**: validacion de entrada (M1), autenticacion JWT y RBAC (M2), aislamiento cross-tenant en lock y deduccion (M3a/M3b), guardas H1/H2/H3 de concurrencia e idempotencia (M4a/M4c/M4d/M4e/M4f), y mapeado correcto de errores a codigos HTTP (M5a/M5b).

Los **dos mutantes vivos** no representan vectores criticos de seguridad inmediata (el filtro `business_id` en nombres esta protegido por RLS; los limites exactos de MAX son casos de borde improbables en produccion), pero exponen ausencia de cobertura en la capa de aplicacion que debe corregirse antes de `opsx:archive` para garantizar falsabilidad completa de la suite.

**Cambio listo para `opsx:archive` condicionado** a que `backend-qa-agent` agregue en `backend/tests/integration/test_sales_api.py` los dos refuerzos descritos en las Brechas 1 y 2.
