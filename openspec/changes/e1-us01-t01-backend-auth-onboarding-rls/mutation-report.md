# 🔬 REPORTE DE MUTATION TESTING Y FALSABILIDAD: e1-us01-t01-backend-auth-onboarding-rls

## 1. Veredicto de Falsabilidad
- **Estado:** `[TESTS COMPLACIENTES DETECTADOS]`
- **Modo de Ejecución:** `Catálogo Canónico M1–M5` (`mutation_cmd: none` en `design.md`; ejecutado sobre copia temporal aislada de `backend/` posteriormente eliminada)
- **Tests Auditados:** `backend/tests/unit/test_auth_schemas.py`, `backend/tests/integration/test_auth_onboarding.py` (y verificación cruzada de los 5 mutantes sobrevivientes contra toda la suite `backend/tests/`, 47 tests totales)
- **Tasa de Mutantes Eliminados:** `3/5` categorías canónicas `M1–M5` blindadas (`60%`) — `18/23` variantes discretas eliminadas (`78.3%`), con **5 mutantes sobrevivientes** (`M3d`, `M3e`, `M3g`, `M3h`, `M4c1`)

---

## 2. Matriz de Mutaciones Evaluadas

### Resumen Canónico M1–M5

| ID | Mutación | Archivo Mutado (`backend/app`) | Archivo de Test (`backend/tests`) | ¿Atrapó el Fallo? | Resultado |
|---|---|---|---|---|---|
| M1 | Eliminación/relajación de validación (`ZoneInfo` y `country`) | `app/modules/auth/schemas.py` | `tests/unit/test_auth_schemas.py` | Sí (`2/2` variantes) | 🗑 Eliminado |
| M2 | Inversión u omisión de guard RBAC/auth (`get_current_user`, `get_current_tenant`, firma JWT) | `app/core/security.py` | `tests/integration/test_auth_onboarding.py` | Sí (`3/3` variantes) | 🗑 Eliminado |
| M3 | Omisión de `SET LOCAL ROLE app_api`, `set_rls_user_context` o `set_rls_business_context` | `app/core/db.py`, `app/modules/auth/repository.py` | `tests/integration/test_auth_onboarding.py` (y `backend/tests/` completo) | Parcial (`4/8` variantes; `M3d`, `M3e`, `M3g`, `M3h` sobreviven) | 🧟 Vivo |
| M4 | Mutación de regla de dominio (`requires_onboarding`, `role="owner"`, `business_id`) | `app/modules/auth/service.py`, `app/modules/auth/repository.py` | `tests/integration/test_auth_onboarding.py` (y `backend/tests/` completo) | Parcial (`4/5` variantes; `M4c1` sobrevive) | 🧟 Vivo |
| M5 | Enmascaramiento de excepción o status `200`/`500` en lugar de `401`/`409` | `app/modules/auth/router.py`, `app/modules/auth/service.py` | `tests/integration/test_auth_onboarding.py` | Sí (`5/5` variantes) | 🗑 Eliminado |

### Detalle de Variantes Evaluadas en Entorno Aislado

Baseline verificado en la copia temporal antes de mutar: `26 passed` (`test_auth_schemas.py` + `test_auth_onboarding.py`) y `47 passed` (suite completa `backend/tests/`).

| Variante | Descripción de la Mutación | Archivo Mutado | Tests que Fallaron / Resultado | Estado |
|---|---|---|---|---|
| `M1a` | Omitir `ZoneInfo(cleaned)` en `_validate_iana_timezone` | `app/modules/auth/schemas.py` | Fallan `test_onboarding_rejects_invalid_or_unrecognized_iana_timezone[Invalid/Timezone]` y `[Mars/Olympus]` (`2 failed, 24 passed`) | 🗑 Eliminado |
| `M1b` | Omitir `cleaned not in COUNTRY_TIMEZONES` en `OnboardingRequest.validate_country` | `app/modules/auth/schemas.py` | Falla `test_onboarding_rejects_unsupported_or_invalid_country_or_blank_name[payload0]` (`1 failed, 25 passed`) | 🗑 Eliminado |
| `M2a` | Omitir rechazo `401` cuando falta cookie en `get_current_user` (devolver `CurrentUser` anónimo) | `app/core/security.py` | Fallan `test_onboarding_unauthenticated_returns_401` y `test_rls_request_lacking_business_context_blocked` (`2 failed, 24 passed`) | 🗑 Eliminado |
| `M2b` | Omitir guard `403` (`if current_user.business_id is None`) en `get_current_tenant` | `app/core/security.py` | Falla `test_rls_request_lacking_business_context_blocked` (`1 failed, 25 passed`) | 🗑 Eliminado |
| `M2c` | Desactivar `verify_signature: False` en `decode_access_token` | `app/core/security.py` | Falla `test_onboarding_unauthenticated_returns_401` (`1 failed, 25 passed`) | 🗑 Eliminado |
| `M3a` | Omitir `SET LOCAL ROLE app_api` en `set_rls_user_context` | `app/core/db.py` | Falla `test_rls_valid_tenant_context_and_cross_tenant_isolation` (`1 failed, 25 passed`) | 🗑 Eliminado |
| `M3b` | Omitir `set_rls_business_context` en `get_tenant_db` | `app/core/db.py` | Falla `test_rls_valid_tenant_context_and_cross_tenant_isolation` (`1 failed, 25 passed`) | 🗑 Eliminado |
| `M3c` | Omitir `set_rls_user_context` en `get_tenant_db` | `app/core/db.py` | Falla `test_rls_valid_tenant_context_and_cross_tenant_isolation` (`1 failed, 25 passed`) | 🗑 Eliminado |
| `M3d` | Omitir `await set_rls_user_context(session, current_user.user_id)` en `get_user_db` | `app/core/db.py` | **No falla ningún test** (`26 passed` / `47 passed` en suite completa) | 🧟 **Vivo** |
| `M3e` | Omitir `await set_rls_user_context(self._session, user_id)` en `AuthRepository.get_user_membership` | `app/modules/auth/repository.py` | **No falla ningún test** (`26 passed` / `47 passed` en suite completa) | 🧟 **Vivo** |
| `M3f` | Omitir solo `await set_rls_business_context(self._session, membership.business_id)` en `AuthRepository.get_user_membership` | `app/modules/auth/repository.py` | Fallan `test_login_success_with_existing_business` y `test_rls_login_membership_lookup_no_deadlock_and_isolates_users` (`2 failed, 24 passed`) | 🗑 Eliminado |
| `M3g` | Omitir `set_rls_user_context` y `set_rls_business_context` en `AuthRepository.create_business_with_owner` | `app/modules/auth/repository.py` | **No falla ningún test** (`26 passed` / `47 passed` en suite completa) | 🧟 **Vivo** |
| `M3h` | Omitir `set_rls_user_context` y `set_rls_business_context` en `AuthRepository.get_user_membership` | `app/modules/auth/repository.py` | **No falla ningún test** (`26 passed` / `47 passed` en suite completa) | 🧟 **Vivo** |
| `M4a` | Invertir `requires_onboarding=True` a `False` en `AuthService.login` | `app/modules/auth/service.py` | Falla `test_login_success_requiring_onboarding` (`1 failed, 25 passed`) | 🗑 Eliminado |
| `M4b` | Alterar `role="owner"` a `"cashier"` en `AuthService.onboard` | `app/modules/auth/service.py` | Fallan `test_onboarding_success_with_country_timezone_resolution` y `test_onboarding_success_with_explicit_valid_iana_timezone` (`2 failed, 24 passed`) | 🗑 Eliminado |
| `M4c1` | Omitir pre-chequeo `if current_user.business_id is not None: raise BusinessAlreadyExistsError(...)` en `AuthService.onboard` | `app/modules/auth/service.py` | **No falla ningún test** (`26 passed` / `47 passed` en suite completa) | 🧟 **Vivo** |
| `M4c2` | Pasar `business_id=None` en `create_access_token` dentro de `AuthService.onboard` | `app/modules/auth/service.py` | Falla `test_onboarding_success_with_country_timezone_resolution` (`1 failed, 25 passed`) | 🗑 Eliminado |
| `M4d` | Alterar `role="owner"` a `"cashier"` en `AuthRepository.create_business_with_owner` | `app/modules/auth/repository.py` | Falla `test_onboarding_success_with_country_timezone_resolution` (`1 failed, 25 passed`) | 🗑 Eliminado |
| `M5a` | Devolver `500` en lugar de `401` ante `InvalidCredentialsError` en `router.login` | `app/modules/auth/router.py` | Falla `test_login_invalid_credentials_returns_401_without_cookie` (`1 failed, 25 passed`) | 🗑 Eliminado |
| `M5b` | Devolver `500` en lugar de `409` ante `BusinessAlreadyExistsError` en `router.onboarding` | `app/modules/auth/router.py` | Fallan `test_onboarding_duplicate_business_returns_409` y `test_onboarding_concurrent_requests_enforce_single_business_no_orphans` (`2 failed, 24 passed`) | 🗑 Eliminado |
| `M5c` | No convertir `IntegrityError` (`23505`) en `BusinessAlreadyExistsError` en `AuthService.onboard` | `app/modules/auth/service.py` | Fallan `test_onboarding_duplicate_business_returns_409` y `test_onboarding_concurrent_requests_enforce_single_business_no_orphans` (`2 failed, 24 passed`) | 🗑 Eliminado |
| `M5d` | Devolver `200` en lugar de `401` ante `InvalidCredentialsError` en `router.login` | `app/modules/auth/router.py` | Falla `test_login_invalid_credentials_returns_401_without_cookie` (`1 failed, 10 passed`) | 🗑 Eliminado |
| `M5e` | Devolver `200` en lugar de `409` ante `BusinessAlreadyExistsError` en `router.onboarding` | `app/modules/auth/router.py` | Fallan `test_onboarding_duplicate_business_returns_409` y `test_onboarding_concurrent_requests_enforce_single_business_no_orphans` (`2 failed, 9 passed`) | 🗑 Eliminado |

---

## 3. Brechas de Falsabilidad y Acción Requerida

Se detectaron **5 mutantes sobrevivientes** agrupados en **3 brechas de falsabilidad** reales dentro de `backend/tests/` que deben ser reforzadas por `backend-qa-agent` antes de considerar la suite blindada:

### Brecha 1 (Crítica — `M3e`, `M3h`, `M3g`): Falso positivo RLS en `AuthRepository` porque los tests de integración corren conectados como `postgres` (`BYPASSRLS`)
- **Mutantes vivos:** `M3e` (`repository.py:get_user_membership` sin `set_rls_user_context`), `M3h` (`repository.py:get_user_membership` sin `set_rls_user_context` ni `set_rls_business_context`), `M3g` (`repository.py:create_business_with_owner` sin `set_rls_user_context` ni `set_rls_business_context`).
- **Causa raíz:** `DATABASE_URL` en pruebas conecta como `postgres` (superusuario con `BYPASSRLS`), y `AuthRepository` obtiene su `AsyncSession` vía `get_db()` sin rol previo. Al suprimir `SET LOCAL ROLE app_api` / `set_rls_*` en `AuthRepository`, las consultas y escrituras se ejecutan como `postgres` saltándose por completo las políticas RLS de `businesses` y `business_users`, y la cláusula SQL `.where(BusinessUser.user_id == user_id)` enmascara el fallo de aislamiento en `test_rls_login_membership_lookup_no_deadlock_and_isolates_users`. Ningún test verifica qué rol efectivo (`current_user == 'app_api'`) ni qué settings (`app.current_user_id`, `app.current_business_id`) están activos dentro de las transacciones de `AuthRepository`.
- **Refuerzo requerido en `backend/tests/integration/test_auth_onboarding.py`:**
  1. Verificar explícitamente (p. ej. mediante event listener de SQLAlchemy `before_cursor_execute` / `execute_options` o envolviendo/espiando la sesión de `get_db` en un test dedicado de login y onboarding) que tanto `AuthRepository.get_user_membership` como `AuthRepository.create_business_with_owner` ejecutan `SET LOCAL ROLE app_api`, `set_config('app.current_user_id', ...)` y `set_config('app.current_business_id', ...)` antes de consultar/insertar en `business_users` y `businesses`.
  2. Complementariamente, añadir un test que ejecute `AuthRepository` con una sesión cuyo rol inicial sea no-privilegiado sin `BYPASSRLS` (o verificar que bajo `app_api` un `SELECT` sin `.where(...)` dentro de la misma transacción solo ve la fila del `user_id` / `business_id` del contexto).

### Brecha 2 (Alta — `M3d`): Dependencia core `get_user_db` sin cobertura de pruebas
- **Mutante vivo:** `M3d` (`app/core/db.py:get_user_db` sin `await set_rls_user_context(session, current_user.user_id)`).
- **Causa raíz:** `test_rls_valid_tenant_context_and_cross_tenant_isolation` y `test_rls_request_lacking_business_context_blocked` prueban `get_tenant_db`, pero ningún test unitario ni de integración invoca `get_user_db`.
- **Refuerzo requerido en `backend/tests/integration/test_auth_onboarding.py`:**
  1. Añadir un test con `probe_app` que utilice `Depends(get_user_db)` (con cookie JWT sin `business_id`) y verifique `current_user == "app_api"`, `current_setting('app.current_user_id', true) == user_id`, rechazo `401` si no está autenticado y aislamiento RLS de `business_users` para el usuario autenticado.

### Brecha 3 (Media — `M4c1`): Pre-chequeo de dominio `current_user.business_id is not None` en `AuthService.onboard` no ejercitado
- **Mutante vivo:** `M4c1` (`app/modules/auth/service.py:onboard` omitiendo `if current_user.business_id is not None: raise BusinessAlreadyExistsError(...)`).
- **Causa raíz:** `test_onboarding_duplicate_business_returns_409` envía `_make_jwt_cookie(user_id=user_id, business_id=None)`, por lo que solo ejercita la captura de `IntegrityError` (`23505`) en BD y nunca la guardia temprana de dominio cuando el JWT ya incluye un `business_id`.
- **Refuerzo requerido en `backend/tests/unit/` o `backend/tests/integration/test_auth_onboarding.py`:**
  1. Añadir un test (p. ej. unitario con repositorio espía o integración con JWT que incluya `business_id` y aserción de que `create_business_with_owner` no es invocado) que envíe una sesión con `business_id != None` a `POST /api/v1/auth/onboarding` (o `AuthService.onboard`) y verifique `409 Conflict` (`code == "BUSINESS_ALREADY_EXISTS"`) sin llegar a ejecutar `INSERT` en BD.

### Observaciones Adicionales de Endurecimiento (No Bloques M1–M5 pero Recomendadas)
- En `test_onboarding_unauthenticated_returns_401`, agregar un caso con JWT bien formado firmado con un secreto distinto (`wrong-secret`) para verificar explícitamente la validación de firma en `decode_access_token` además de tokens malformados y expirados.
- En `test_onboarding_duplicate_business_returns_409`, asertar además `response.json()["code"] == "BUSINESS_ALREADY_EXISTS"` para validar el contrato de error además del código HTTP `409`.
