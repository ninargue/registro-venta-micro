# 🔬 REPORTE DE MUTATION TESTING Y FALSABILIDAD: us-02-t04b-backend

## 1. Veredicto de Falsabilidad
- **Estado:** `[TESTS BLINDADOS]`
- **Modo de Ejecución:** `Catálogo Canónico M1–M5`
- **Tests Auditados:** `backend/tests/unit/test_catalog_schemas.py`, `backend/tests/integration/test_catalog_products.py`
- **Tasa de Mutantes Eliminados:** `5/5` (`100%`)

## 2. Matriz de Mutaciones Evaluadas
| ID | Mutación | Archivo Mutado (`backend/app`) | Archivo de Test (`backend/tests`) | ¿Atrapó el Fallo? | Resultado |
|---|---|---|---|---|---|
| M1 | Eliminación/relajación de validación (`ProductUpdate`: omitir rechazo de payload vacío `{}` / campos `null` obligatorios) | `backend/app/modules/catalog/schemas.py` | `backend/tests/unit/test_catalog_schemas.py` (`test_product_update_rejects_empty_payload_or_only_ignored_fields`) y `backend/tests/integration/test_catalog_products.py` (`test_patch_rejects_explicit_null_on_non_nullable_fields_or_empty_payload`) | Sí | 🗑 Eliminado |
| M2 | Inversión u omisión de guard RBAC/auth (`update_product`: sustituir `Depends(require_owner)` por `Depends(get_current_tenant)` permitiendo rol `cashier`) | `backend/app/modules/catalog/router.py` | `backend/tests/integration/test_catalog_products.py` (`test_patch_cashier_role_rejected_with_403_forbidden`) | Sí | 🗑 Eliminado |
| M3 | Omisión de filtro `tenant_id`/IDOR o bypass RLS (sustituir `get_tenant_db` por `get_db` y eliminar predicado `Product.business_id == business_id` en `CatalogRepository.update_product`) | `backend/app/modules/catalog/router.py`, `backend/app/modules/catalog/repository.py` | `backend/tests/integration/test_catalog_products.py` (`test_patch_cross_tenant_product_id_returns_404_and_leaves_target_unmodified`) | Sí | 🗑 Eliminado |
| M4 | Mutación de operador/límite en regla de dominio (`ProductUpdate.sale_price`: relajar `gt=Decimal("0")` a `ge=Decimal("0")`) | `backend/app/modules/catalog/schemas.py` | `backend/tests/unit/test_catalog_schemas.py` (`test_product_update_rejects_out_of_range_bounds[sale_price-0.00]`) y `backend/tests/integration/test_catalog_products.py` (`test_patch_rejects_non_positive_sale_price_negative_cost_or_negative_stock`) | Sí | 🗑 Eliminado |
| M5 | Enmascaramiento de excepción o status `2xx`/`500` (`update_product`: mapear `ProductNotFoundError` a `HTTP 400` en lugar de `404 PRODUCT_NOT_FOUND`) | `backend/app/modules/catalog/router.py` | `backend/tests/integration/test_catalog_products.py` (`test_patch_non_existent_product_id_returns_404`) | Sí | 🗑 Eliminado |

## 3. Brechas de Falsabilidad y Acción Requerida
- **Si `[TESTS BLINDADOS]`:** Suite Backend-TDD verificada como robusta y falsable. Cambio listo para `opsx:archive`.
  - **Evidencia de aislamiento y limpieza:** Todas las mutaciones `M1–M5` fueron ejecutadas sobre una copia temporal aislada en `$env:TEMP\mut-us-02-t04b-backend` sin tocar jamás el árbol de trabajo en vivo (`backend/app` ni `backend/tests`), y el directorio temporal fue eliminado por completo al finalizar (`TEMP_DIR_EXISTS=False`).
