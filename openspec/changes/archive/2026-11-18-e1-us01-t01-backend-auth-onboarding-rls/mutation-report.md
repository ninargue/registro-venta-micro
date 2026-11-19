# 🔬 REPORTE DE MUTATION TESTING Y FALSABILIDAD: e1-us01-t01-backend-auth-onboarding-rls

## 1. Veredicto de Falsabilidad
- **Estado:** `[TESTS BLINDADOS]`
- **Modo de Ejecución:** `Catálogo Canónico M1–M5` (`mutation_cmd: none` en `design.md`; re-ejecutado tras refuerzo de `backend-qa-agent` sobre copia temporal aislada de `backend/` posteriormente eliminada, `TMP_EXISTS=False`)
- **Tests Auditados:** `backend/tests/unit/test_auth_schemas.py`, `backend/tests/integration/test_auth_onboarding.py` (`28 passed` en los archivos auditados; `49 passed` en la suite completa de `backend/tests/`)
- **Tasa de Mutantes Eliminados:** `5/5` categorías canónicas `M1–M5` (`100%`) — `27/27` variantes discretas eliminadas (`100%`)

---

## 2. Matriz de Mutaciones Evaluadas

### Resumen Canónico M1–M5

| ID | Mutación | Archivo Mutado (`backend/app`) | Archivo de Test (`backend/tests`) | ¿Atrapó el Fallo? | Resultado |
|---|---|---|---|---|---|
| M1 | Eliminación/relajación de validación (`ZoneInfo` y `country`) | `app/modules/auth/schemas.py` | `tests/unit/test_auth_schemas.py` | Sí (`2/2` variantes) | 🗑 Eliminado |
| M2 | Inversión u omisión de guard RBAC/auth (`get_current_user`, `get_current_tenant`, firma y expiración JWT) | `app/core/security.py` | `tests/integration/test_auth_onboarding.py` | Sí (`4/4` variantes) | 🗑 Eliminado |
| M3 | Omisión de `SET LOCAL ROLE app_api`, `set_rls_user_context` o `set_rls_business_context` | `app/core/db.py`, `app/modules/auth/repository.py` | `tests/integration/test_auth_onboarding.py` | Sí (`10/10` variantes) | 🗑 Eliminado |
| M4 | Mutación de regla de dominio (`requires_onboarding`, `role="owner"`, `business_id` en JWT y pre-chequeo) | `app/modules/auth/service.py`, `app/modules/auth/repository.py` | `tests/integration/test_auth_onboarding.py` | Sí (`5/5` variantes) | 🗑 Eliminado |
| M5 | Enmascaramiento de excepción, código de error o status `200`/`500` en lugar de `401`/`409` | `app/modules/auth/router.py`, `app/modules/auth/service.py` | `tests/integration/test_auth_onboarding.py` | Sí (`6/6` variantes) | 🗑 Eliminado |

### Detalle de Variantes Evaluadas en Entorno Aislado (Ejecución Fail-Fast `-x`)

Baseline verificado en la copia temporal aislada antes de mutar: `28 passed` (`tests/unit/test_auth_schemas.py` + `tests/integration/test_auth_onboarding.py`) y `49 passed` en la suite completa (`backend/tests/`).

| Variante | Descripción de la Mutación | Archivo Mutado | Primer Test que Atrapó el Fallo (`-x`) | Estado |
|---|---|---|---|---|
| `M1a` | Omitir `ZoneInfo(cleaned)` en `_validate_iana_timezone` | `app/modules/auth/schemas.py` | `test_auth_schemas.py::test_onboarding_rejects_invalid_or_unrecognized_iana_timezone[Invalid/Timezone]` (`1 failed`) | 🗑 Eliminado |
| `M1b` | Omitir `cleaned not in COUNTRY_TIMEZONES` en `OnboardingRequest.validate_country` | `app/modules/auth/schemas.py` | `test_auth_schemas.py::test_onboarding_rejects_unsupported_or_invalid_country_or_blank_name[payload0]` (`1 failed`) | 🗑 Eliminado |
| `M2a` | Omitir rechazo `401` cuando falta cookie en `get_current_user` (devolver `CurrentUser` anónimo) | `app/core/security.py` | `test_auth_onboarding.py::test_onboarding_unauthenticated_returns_401` (`1 failed`) | 🗑 Eliminado |
| `M2b` | Omitir guard `403` (`if current_user.business_id is None`) en `get_current_tenant` | `app/core/security.py` | `test_auth_onboarding.py::test_rls_request_lacking_business_context_blocked` (`1 failed`) | 🗑 Eliminado |
| `M2c` | Desactivar `verify_signature: False` en `decode_access_token` | `app/core/security.py` | `test_auth_onboarding.py::test_onboarding_unauthenticated_returns_401` (`1 failed`) | 🗑 Eliminado |
| `M2d` | Desactivar `verify_exp: False` en `decode_access_token` | `app/core/security.py` | `test_auth_onboarding.py::test_onboarding_unauthenticated_returns_401` (`1 failed`) | 🗑 Eliminado |
| `M3a` | Omitir `SET LOCAL ROLE app_api` en `set_rls_user_context` | `app/core/db.py` | `test_auth_onboarding.py::test_login_success_with_existing_business` (`1 failed`) | 🗑 Eliminado |
| `M3b` | Omitir `set_rls_business_context` en `get_tenant_db` | `app/core/db.py` | `test_auth_onboarding.py::test_rls_valid_tenant_context_and_cross_tenant_isolation` (`1 failed`) | 🗑 Eliminado |
| `M3c` | Omitir `set_rls_user_context` en `get_tenant_db` | `app/core/db.py` | `test_auth_onboarding.py::test_rls_valid_tenant_context_and_cross_tenant_isolation` (`1 failed`) | 🗑 Eliminado |
| `M3d` | Omitir `await set_rls_user_context(session, current_user.user_id)` en `get_user_db` *(brecha previa)* | `app/core/db.py` | `test_auth_onboarding.py::test_rls_user_db_context_and_isolation` (`1 failed`) | 🗑 Eliminado |
| `M3e` | Omitir `set_rls_user_context` en `AuthRepository.get_user_membership` *(brecha previa)* | `app/modules/auth/repository.py` | `test_auth_onboarding.py::test_login_success_with_existing_business` (`1 failed`) | 🗑 Eliminado |
| `M3f` | Omitir solo `set_rls_business_context` en `AuthRepository.get_user_membership` | `app/modules/auth/repository.py` | `test_auth_onboarding.py::test_login_success_with_existing_business` (`1 failed`) | 🗑 Eliminado |
| `M3g` | Omitir `set_rls_user_context` y `set_rls_business_context` en `AuthRepository.create_business_with_owner` *(brecha previa)* | `app/modules/auth/repository.py` | `test_auth_onboarding.py::test_onboarding_success_with_country_timezone_resolution` (`1 failed`) | 🗑 Eliminado |
| `M3h` | Omitir `set_rls_user_context` y `set_rls_business_context` en `AuthRepository.get_user_membership` *(brecha previa)* | `app/modules/auth/repository.py` | `test_auth_onboarding.py::test_login_success_with_existing_business` (`1 failed`) | 🗑 Eliminado |
| `M3i` | Omitir solo `set_rls_user_context` en `AuthRepository.create_business_with_owner` | `app/modules/auth/repository.py` | `test_auth_onboarding.py::test_onboarding_success_with_country_timezone_resolution` (`1 failed`) | 🗑 Eliminado |
| `M3j` | Omitir solo `set_rls_business_context` en `AuthRepository.create_business_with_owner` | `app/modules/auth/repository.py` | `test_auth_onboarding.py::test_onboarding_success_with_country_timezone_resolution` (`1 failed`) | 🗑 Eliminado |
| `M4a` | Invertir `requires_onboarding=True` a `False` en `AuthService.login` | `app/modules/auth/service.py` | `test_auth_onboarding.py::test_login_success_requiring_onboarding` (`1 failed`) | 🗑 Eliminado |
| `M4b` | Alterar `role="owner"` a `"cashier"` en `AuthService.onboard` | `app/modules/auth/service.py` | `test_auth_onboarding.py::test_onboarding_success_with_country_timezone_resolution` (`1 failed`) | 🗑 Eliminado |
| `M4c1` | Omitir pre-chequeo `if current_user.business_id is not None: raise BusinessAlreadyExistsError(...)` en `AuthService.onboard` *(brecha previa)* | `app/modules/auth/service.py` | `test_auth_onboarding.py::test_onboarding_with_existing_business_in_jwt_returns_409_without_insert` (`1 failed`) | 🗑 Eliminado |
| `M4c2` | Pasar `business_id=None` en `create_access_token` dentro de `AuthService.onboard` | `app/modules/auth/service.py` | `test_auth_onboarding.py::test_onboarding_success_with_country_timezone_resolution` (`1 failed`) | 🗑 Eliminado |
| `M4d` | Alterar `role="owner"` a `"cashier"` en `AuthRepository.create_business_with_owner` | `app/modules/auth/repository.py` | `test_auth_onboarding.py::test_onboarding_success_with_country_timezone_resolution` (`1 failed`) | 🗑 Eliminado |
| `M5a` | Devolver `500` en lugar de `401` ante `InvalidCredentialsError` en `router.login` | `app/modules/auth/router.py` | `test_auth_onboarding.py::test_login_invalid_credentials_returns_401_without_cookie` (`1 failed`) | 🗑 Eliminado |
| `M5b` | Devolver `500` en lugar de `409` ante `BusinessAlreadyExistsError` en `router.onboarding` | `app/modules/auth/router.py` | `test_auth_onboarding.py::test_onboarding_duplicate_business_returns_409` (`1 failed`) | 🗑 Eliminado |
| `M5c` | No convertir `IntegrityError` (`23505`) en `BusinessAlreadyExistsError` en `AuthService.onboard` | `app/modules/auth/service.py` | `test_auth_onboarding.py::test_onboarding_duplicate_business_returns_409` (`1 failed`) | 🗑 Eliminado |
| `M5d` | Devolver `200` en lugar de `401` ante `InvalidCredentialsError` en `router.login` | `app/modules/auth/router.py` | `test_auth_onboarding.py::test_login_invalid_credentials_returns_401_without_cookie` (`1 failed`) | 🗑 Eliminado |
| `M5e` | Devolver `200` en lugar de `409` ante `BusinessAlreadyExistsError` en `router.onboarding` | `app/modules/auth/router.py` | `test_auth_onboarding.py::test_onboarding_duplicate_business_returns_409` (`1 failed`) | 🗑 Eliminado |
| `M5f` | Alterar `code="BUSINESS_ALREADY_EXISTS"` en respuesta `409` de `router.onboarding` | `app/modules/auth/router.py` | `test_auth_onboarding.py::test_onboarding_duplicate_business_returns_409` (`1 failed`) | 🗑 Eliminado |

---

## 3. Brechas de Falsabilidad y Acción Requerida

- **`[TESTS BLINDADOS]`:** Suite Backend-TDD verificada como robusta y falsable tras el refuerzo aplicado en `backend/tests/integration/test_auth_onboarding.py`:
  - **Brecha 1 cerrada (`M3e`, `M3h`, `M3g`, `M3i`, `M3j`):** `_capture_sql_statements()` ahora verifica en `test_login_success_with_existing_business` y `test_onboarding_success_with_country_timezone_resolution` la ejecución previa de `SET LOCAL ROLE app_api`, `set_config('app.current_user_id', ...)` y `set_config('app.current_business_id', ...)` antes de las consultas/inserciones en `business_users` y `businesses`.
  - **Brecha 2 cerrada (`M3d`):** `test_rls_user_db_context_and_isolation` valida `app.core.db.get_user_db` comprobando `401` sin sesión, `current_user == "app_api"`, `app.current_user_id` y aislamiento RLS sobre `business_users`.
  - **Brecha 3 cerrada (`M4c1`):** `test_onboarding_with_existing_business_in_jwt_returns_409_without_insert` valida que un JWT con `business_id` preexistente responde `409 Conflict` (`code == "BUSINESS_ALREADY_EXISTS"`) sin ejecutar `INSERT INTO businesses`.
  - **Endurecimiento adicional verificado (`M2c`, `M5f`):** `test_onboarding_unauthenticated_returns_401` incluye JWT firmado con secreto incorrecto (`res_wrong_sig`), y los tests de `409` validan explícitamente `code == "BUSINESS_ALREADY_EXISTS"`.
- Cambio listo para `opsx:archive`.
