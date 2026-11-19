# 🔬 REPORTE DE MUTATION TESTING Y FALSABILIDAD: fix-53-businesses-rls-db

## 1. Veredicto de Falsabilidad
- **Estado:** `[TESTS BLINDADOS]`
- **Tests Auditados:** `backend/tests/integration/test_db_businesses.py` (20 tests de integración DB — `21 passed in 8.00s` en suite completa `uv run pytest -v`)
- **Tasa de Mutantes Eliminados:** `19/19` (`100.0%`)

> Todas las mutaciones fueron ejecutadas contra la base PostgreSQL local de pruebas (`DATABASE_URL` en `backend/.env`) dentro de transacciones efímeras con `ROLLBACK` completo (`businesses=48`, `business_users=12` antes y después de la auditoría y tras correr los 20 tests de `test_db_businesses.py`, sin persistir ninguna mutación ni fila).

---

## 2. Matriz de Mutaciones Evaluadas

| ID | Mutación | Archivo de Test | ¿Atrapó el Fallo? | Resultado |
|---|---|---|---|---|
| M1a | Omitir `UNIQUE (user_id)` (`uq_business_users_user_id`) en `business_users` | `backend/tests/integration/test_db_businesses.py::test_business_users_rejects_duplicate_user_id` | Sí | 🗑 Eliminado |
| M1b | Omitir `CHECK (role IN ('owner', 'cashier'))` (`chk_business_users_role_valid`) en `business_users` | `backend/tests/integration/test_db_businesses.py::test_business_users_rejects_invalid_role` | Sí | 🗑 Eliminado |
| M1c | Omitir `CHECK (char_length(country) = 2)` (`chk_businesses_country_length`) en `businesses` | `backend/tests/integration/test_db_businesses.py::test_insert_business_rejects_invalid_country_length` (`country='A'`, `23514`) | Sí | 🗑 Eliminado |
| M1d | Omitir `CHECK (char_length(trim(name)) > 0)` (`chk_businesses_name_not_empty`) en `businesses` | `backend/tests/integration/test_db_businesses.py::test_insert_business_rejects_invalid_country_length` (`name='   '`, `23514`) | Sí | 🗑 Eliminado |
| M2a | Omitir FK `fk_business_users_business_id` (`ON DELETE CASCADE`) en `business_users` | `backend/tests/integration/test_db_businesses.py::test_business_users_cascade_delete` | Sí (`count(*) == 1 != 0`) | 🗑 Eliminado |
| M2b | Insertar FK huérfana (`business_id` inexistente) en `business_users` omitiendo FK | `backend/tests/integration/test_db_businesses.py::test_business_users_rejects_orphan_business_id` (`23503`) | Sí | 🗑 Eliminado |
| M3a | Deshabilitar RLS (`ALTER TABLE business_users DISABLE ROW LEVEL SECURITY`) | `backend/tests/integration/test_db_businesses.py::test_rls_business_users_*`, `test_app_api_cannot_bypass_rls_or_truncate` | Sí (fuga cross-tenant detectada) | 🗑 Eliminado |
| M3b | Revertir política `INSERT` (`business_users_insert_own_user`) a `WITH CHECK (true)` | `backend/tests/integration/test_db_businesses.py::test_rls_business_users_insert_impersonated_user_rejected`, `test_rls_business_users_insert_without_user_context_rejected` | Sí | 🗑 Eliminado |
| M3c | Omitir validación de `app.current_business_id` en `business_users_insert_own_user` | `backend/tests/integration/test_db_businesses.py::test_rls_business_users_insert_mismatched_business_id_rejected` | Sí | 🗑 Eliminado |
| M3d | Omitir rama `app.current_user_id` en `business_users_select_isolation` | `backend/tests/integration/test_db_businesses.py::test_rls_business_users_login_select_by_current_user_id` | Sí (retorna 0 filas) | 🗑 Eliminado |
| M3e | Relajar `business_users_update_isolation` a `WITH CHECK (true)` | `backend/tests/integration/test_db_businesses.py::test_rls_business_users_update_hijack_rejected` (`app.current_user_id` fijado + `UPDATE` con y sin `WHERE`) | Sí (ambos hijacks pasan y rompen el test) | 🗑 Eliminado |
| M3f | Relajar `business_users_delete_isolation` a `USING (true)` | `backend/tests/integration/test_db_businesses.py::test_app_api_cannot_bypass_rls_or_truncate` (`DELETE FROM business_users;` sin `WHERE` + `remaining_b2 == 1`) | Sí (`rowcount=14 != 1` y `remaining_b2=0 != 1`) | 🗑 Eliminado |
| M3f2 | Omitir política `business_users_delete_isolation` (default-deny en `DELETE`) | `backend/tests/integration/test_db_businesses.py::test_app_api_performs_permitted_dml_under_rls` (`del_own.rowcount == 1`) | Sí (`rowcount=0 != 1`) | 🗑 Eliminado |
| M3g | Desactivar `FORCE ROW LEVEL SECURITY` (`NO FORCE ROW LEVEL SECURITY`) en `business_users` | `backend/tests/integration/test_db_businesses.py::test_app_api_role_exists_without_bypass_or_ownership` (`pg_class.relforcerowsecurity`) | Sí (`relforcerowsecurity=False`) | 🗑 Eliminado |
| M3h | Otorgar `BYPASSRLS` a `app_api` (`ALTER ROLE app_api BYPASSRLS`) | `backend/tests/integration/test_db_businesses.py::test_app_api_role_exists_without_bypass_or_ownership` | Sí | 🗑 Eliminado |
| M3i | Otorgar `TRUNCATE` a `app_api` (`GRANT TRUNCATE ON TABLE business_users TO app_api`) | `backend/tests/integration/test_db_businesses.py::test_app_api_cannot_bypass_rls_or_truncate` | Sí | 🗑 Eliminado |
| M4a | Excepción enmascarada en RLS (quitar `NULLIF` generando `22P02` en vez de `42501`) | `backend/tests/integration/test_db_businesses.py` (`_assert_sqlstate(..., "42501")`) | Sí (`22P02 != 42501`) | 🗑 Eliminado |
| M4b | Excepción enmascarada en constraints (`22001` vs `23514`, `23502`, `23503`, `23505`) | `backend/tests/integration/test_db_businesses.py` (`_assert_sqlstate` en todos los tests negativos del dominio) | Sí (`SQLSTATE` exacto validado) | 🗑 Eliminado |
| M5 | Fuga de datos sin `ROLLBACK` / falta de idempotencia transaccional | `backend/tests/integration/test_db_businesses.py` (20 tests con `tx.rollback()` / `begin()` fallido) | Sí (`BEFORE: (48, 12)` → `20 passed` → `AFTER: (48, 12)`) | 🗑 Eliminado |

---

## 3. Brechas de Falsabilidad y Acción Requerida
- **Estado `[TESTS BLINDADOS]`:** Suite DB-TDD verificada como robusta, transaccional y falsable frente a los 19 mutantes canónicos M1–M5 (`100.0%` eliminados). Todas las brechas detectadas en la primera pasada (`M1c`, `M2b`, `M3e`, `M3f`, `M3g`, `M4b`, `M5b`) fueron remediadas por `db-qa-agent` y verificadas en vivo contra PostgreSQL. Cambio listo para archivo en OpenSpec (`opsx:archive`).
