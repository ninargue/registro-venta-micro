# 🔬 REPORTE DE MUTATION TESTING Y FALSABILIDAD: fix-53-businesses-rls-db

## 1. Veredicto de Falsabilidad
- **Estado:** `[TESTS COMPLACIENTES DETECTADOS]`
- **Tests Auditados:** `backend/tests/integration/test_db_businesses.py` (19 tests totales: 12 nuevos de `fix-53-businesses-rls-db` + 7 heredados del dominio en `0002`, usando fixture `db_session` en `backend/tests/conftest.py`)
- **Tasa de Mutantes Eliminados:** `11/18` (`61.1%`) en la suite completa del dominio (`8/11`, `72.7%` en los mutantes directos del cambio `fix-53-businesses-rls-db`)

> Todas las mutaciones fueron ejecutadas contra la base PostgreSQL local de pruebas (`DATABASE_URL` en `backend/.env`) dentro de transacciones efímeras con `ROLLBACK` completo (`businesses=48`, `business_users=12`, 6 políticas RLS y flags `relrowsecurity=true`/`relforcerowsecurity=true` intactos al finalizar).

---

## 2. Matriz de Mutaciones Evaluadas

| ID | Mutación | Archivo de Test | ¿Atrapó el Fallo? | Resultado |
|---|---|---|---|---|
| M1a | Omitir `UNIQUE (user_id)` (`uq_business_users_user_id`) en `business_users` | `backend/tests/integration/test_db_businesses.py::test_business_users_rejects_duplicate_user_id` | Sí | 🗑 Eliminado |
| M1b | Omitir `CHECK (role IN ('owner', 'cashier'))` (`chk_business_users_role_valid`) en `business_users` | `backend/tests/integration/test_db_businesses.py::test_business_users_rejects_invalid_role` | Sí | 🗑 Eliminado |
| M1c | Omitir `CHECK (char_length(country) = 2)` (`chk_businesses_country_length`) en `businesses` | `backend/tests/integration/test_db_businesses.py::test_insert_business_rejects_invalid_country_length` | No (`'ARG'` falla antes por `VARCHAR(2)` con SQLSTATE `22001`) | 🧟 Vivo |
| M2a | Omitir FK `fk_business_users_business_id` (`ON DELETE CASCADE`) en `business_users` | `backend/tests/integration/test_db_businesses.py::test_business_users_cascade_delete` | Sí (`count(*) == 1 != 0`) | 🗑 Eliminado |
| M2b | Insertar FK huérfana (`business_id` inexistente) en `business_users` esperando `23503` | `backend/tests/integration/test_db_businesses.py` (sin test negativo de FK huérfana) | No | 🧟 Vivo |
| M3a | Deshabilitar RLS (`ALTER TABLE business_users DISABLE ROW LEVEL SECURITY`) | `backend/tests/integration/test_db_businesses.py::test_rls_business_users_*`, `test_app_api_cannot_bypass_rls_or_truncate` | Sí (fuga de filas cross-tenant) | 🗑 Eliminado |
| M3b | Revertir política `INSERT` (`business_users_insert_own_user`) a `WITH CHECK (true)` | `backend/tests/integration/test_db_businesses.py::test_rls_business_users_insert_impersonated_user_rejected`, `test_rls_business_users_insert_without_user_context_rejected` | Sí | 🗑 Eliminado |
| M3c | Omitir validación de `app.current_business_id` en `business_users_insert_own_user` | `backend/tests/integration/test_db_businesses.py::test_rls_business_users_insert_mismatched_business_id_rejected` | Sí | 🗑 Eliminado |
| M3d | Omitir rama `app.current_user_id` en `business_users_select_isolation` | `backend/tests/integration/test_db_businesses.py::test_rls_business_users_login_select_by_current_user_id` | Sí (retorna 0 filas) | 🗑 Eliminado |
| M3e | Relajar `business_users_update_isolation` a `WITH CHECK (true)` | `backend/tests/integration/test_db_businesses.py::test_rls_business_users_update_hijack_rejected` | No (protegido accidentalmente por `SELECT` RLS al faltar `app.current_user_id`; con `app.current_user_id` fijado o sin `WHERE`, el hijack pasa con `rowcount = 1`) | 🧟 Vivo |
| M3f | Relajar `business_users_delete_isolation` a `USING (true)` | `backend/tests/integration/test_db_businesses.py::test_app_api_cannot_bypass_rls_or_truncate` | No (`DELETE ... WHERE business_id = :b2` queda oculto por `SELECT` RLS; `DELETE FROM business_users;` sin `WHERE` borra las 14 filas) | 🧟 Vivo |
| M3g | Desactivar `FORCE ROW LEVEL SECURITY` (`NO FORCE ROW LEVEL SECURITY`) en `business_users` | `backend/tests/integration/test_db_businesses.py` (ningún test inspecciona `pg_class.relforcerowsecurity` ni consulta como dueño sin `BYPASSRLS`) | No | 🧟 Vivo |
| M3h | Otorgar `BYPASSRLS` a `app_api` (`ALTER ROLE app_api BYPASSRLS`) | `backend/tests/integration/test_db_businesses.py::test_app_api_role_exists_without_bypass_or_ownership` | Sí | 🗑 Eliminado |
| M3i | Otorgar `TRUNCATE` a `app_api` (`GRANT TRUNCATE ON TABLE business_users TO app_api`) | `backend/tests/integration/test_db_businesses.py::test_app_api_cannot_bypass_rls_or_truncate` | Sí | 🗑 Eliminado |
| M4a | Excepción enmascarada en tests nuevos de `fix-53-businesses-rls-db` (p. ej. quitar `NULLIF` generando `22P02` en vez de `42501`) | `backend/tests/integration/test_db_businesses.py` (6 tests negativos nuevos con `_assert_sqlstate`) | Sí (`_assert_sqlstate` exige `23505` / `42501`) | 🗑 Eliminado |
| M4b | Excepción genérica `(IntegrityError, DBAPIError)` sin validar SQLSTATE en tests heredados de `0002` | `backend/tests/integration/test_db_businesses.py::test_insert_business_rejects_nulls`, `test_insert_business_rejects_invalid_country_length`, `test_business_users_rejects_invalid_role` | No | 🧟 Vivo |
| M5a | Aislamiento transaccional con `ROLLBACK` en los 12 tests nuevos de `fix-53-businesses-rls-db` | `backend/tests/integration/test_db_businesses.py` (líneas 238–652) | Sí (`BEFORE: (48, 12)` → `AFTER: (48, 12)`) | 🗑 Eliminado |
| M5b | Aislamiento transaccional con `ROLLBACK` en tests heredados de `0002` y fixture `db_session` | `backend/tests/integration/test_db_businesses.py` (líneas 10–195) y `backend/tests/conftest.py` | No (`test_insert_business_valid`, `test_business_users_membership_and_valid_role` y `test_rls_isolation_by_session_variable` ejecutan `COMMIT` de 4 filas en `businesses` y 1 en `business_users` por ejecución) | 🧟 Vivo |

---

## 3. Brechas de Falsabilidad y Acción Requerida

Se detectaron **7 mutantes vivos (`3` dentro de los tests nuevos de `fix-53-businesses-rls-db` y `4` en los tests preexistentes del dominio en `0002`)**. Se requiere intervención de `db-qa-agent` sobre `backend/tests/integration/test_db_businesses.py` (y `backend/tests/conftest.py`) antes de considerar la suite blindada:

### A. Brechas críticas en `fix-53-businesses-rls-db` (RLS Bypass M3)
1. **M3e — `test_rls_business_users_update_hijack_rejected` (`business_users_update_isolation` `WITH CHECK`):**
   - *Causa raíz:* El test solo fija `SET LOCAL app.current_business_id = '{b1}'` sin fijar `SET LOCAL app.current_user_id = '{u_a}'` y usa `WHERE user_id = :u_a`. En PostgreSQL, esa cláusula `WHERE` activa la evaluación de la política `FOR SELECT` (`business_users_select_isolation`) también sobre la fila resultante del `UPDATE`. Como `app.current_user_id` está vacío, `SELECT` bloquea el cambio a `b2` incluso si `business_users_update_isolation` tiene `WITH CHECK (true)`. En una sesión real autenticada (con `app.current_user_id = u_a` activo) o en un `UPDATE` sin `WHERE`, el tenant hijack **pasa con `rowcount = 1`**.
   - *Refuerzo requerido:* En `test_rls_business_users_update_hijack_rejected`, fijar también `SET LOCAL app.current_user_id = '{u_a}';` (y/o probar un `UPDATE business_users SET business_id = :b2;` sin `WHERE` en un sub-bloque `begin_nested()`) para aislar y falsar exclusivamente el `WITH CHECK` de `business_users_update_isolation`.
2. **M3f — `test_app_api_cannot_bypass_rls_or_truncate` (`business_users_delete_isolation` `USING`):**
   - *Causa raíz:* `DELETE FROM business_users WHERE business_id = :b2` referencia la columna `business_id` en `WHERE`, por lo que PostgreSQL filtra primero por `business_users_select_isolation`. Al mutar `business_users_delete_isolation` a `USING (true)`, el test sigue pasando (`rowcount == 0`), pero `DELETE FROM business_users;` (sin cláusula `WHERE`) elimina **todas las filas de todos los tenants** (`rowcount = 14` en la prueba efímera). Además, `test_app_api_performs_permitted_dml_under_rls` no ejercita un `DELETE` permitido sobre `business_users` del tenant activo (que detectaría una omisión completa de `business_users_delete_isolation`).
   - *Refuerzo requerido:* En `test_app_api_cannot_bypass_rls_or_truncate`, ejecutar también `DELETE FROM business_users;` (sin `WHERE`) dentro de una transacción con datos de `b1` y `b2` verificando que `rowcount` afecte únicamente a las filas del tenant activo `b1` (0 filas de `b2` borradas). Opcionalmente, verificar en `test_app_api_performs_permitted_dml_under_rls` el `DELETE` permitido dentro de `b1`.
3. **M3g — `FORCE ROW LEVEL SECURITY` (`pg_class.relforcerowsecurity`):**
   - *Causa raíz:* Todos los tests cambian a `app_api` o `authenticated`, roles que no son dueños de las tablas (`tableowner = postgres`), por lo que `ALTER TABLE ... NO FORCE ROW LEVEL SECURITY` no rompe ningún test.
   - *Refuerzo requerido:* Agregar una aserción sobre `pg_class` (`relrowsecurity = true` y `relforcerowsecurity = true` para `businesses` y `business_users` en el esquema `public`), asegurando que la migración mantiene `ENABLE` y `FORCE ROW LEVEL SECURITY`.

### B. Brechas heredadas de `0002` en la suite del dominio (`test_db_businesses.py` / `conftest.py`)
4. **M1c y M4b — `test_insert_business_rejects_invalid_country_length`, `test_insert_business_rejects_nulls` y `test_business_users_rejects_invalid_role`:**
   - *Causa raíz:* Los tres tests usan `with pytest.raises((IntegrityError, DBAPIError)):` sin validar SQLSTATE mediante `_assert_sqlstate`. Además, `test_insert_business_rejects_invalid_country_length` inserta `'ARG'` (3 caracteres), que dispara `22001` (`string_data_right_truncation`) por `VARCHAR(2)` antes que el `CHECK (char_length(country) = 2)` (`23514`). Tampoco existe test para `chk_businesses_name_not_empty` (`''` o `'   '`).
   - *Refuerzo requerido:* Usar `_assert_sqlstate(..., "23502")` para `NOT NULL`, `_assert_sqlstate(..., "23514")` para los `CHECK` constraints, y probar `country = 'A'` (longitud 1) para falsar `chk_businesses_country_length` además de `name = '   '` para `chk_businesses_name_not_empty`.
5. **M2b — Cobertura de FK huérfana (`23503`):**
   - *Causa raíz:* `test_business_users_cascade_delete` cubre `ON DELETE CASCADE`, pero ningún test intenta insertar en `business_users` un `business_id` inexistente verificando `_assert_sqlstate(..., "23503")`.
   - *Refuerzo requerido:* Añadir `test_business_users_rejects_orphan_business_id` intentando insertar con un `business_id` inexistente y validando SQLSTATE `23503` (`foreign_key_violation`).
6. **M5b — Aislamiento transaccional en tests heredados (`0002`) y `conftest.py`:**
   - *Causa raíz:* `test_insert_business_valid`, `test_business_users_membership_and_valid_role` y `test_rls_isolation_by_session_variable` usan `async with db_session.begin():` sin `await tx.rollback()`, acumulando basura persistida (`48` filas en `businesses` y `12` en `business_users` tras 12 ejecuciones).
   - *Refuerzo requerido:* Envolver esos tests (o el fixture `db_session` en `backend/tests/conftest.py`) en transacciones con `ROLLBACK` garantizado (`try ... finally: await tx.rollback()`) para garantizar idempotencia 100% limpia en toda la suite.
