# Verification Report — `e1-us01-t01-backend-auth-onboarding-rls`

- **Cambio:** `e1-us01-t01-backend-auth-onboarding-rls` (Issue `#39` / `US-01-T01`)
- **Verificador:** `backend-qa-agent` (Fase B — `opsx:verify` en modo solo lectura sobre código y tests)
- **Fecha:** 2026-11-18
- **Veredicto:** **[APROBADO]**

---

## 1. Scorecard `opsx:verify`

| Dimensión | Estado | Resultado |
|---|---|---|
| **Completeness** | PASS | `13/13` tareas completadas (`- [x]`) en `tasks.md`; 100% de requisitos de `specs/auth-onboarding/spec.md` implementados. |
| **Correctness** | PASS | `14/14` escenarios Given/When/Then cubiertos y en **VERDE**; suite completa `47 passed` en `20.28s` (`95%` cobertura en `app/`). |
| **Coherence** | PASS | Alineación 1:1 entre `design.md` y `backend/app/`; sin secretos en código ni fugas en DTOs; `alembic check` sin drift (`e4a7c2b91f03`). |

---

## 2. Matriz Técnica de Gates 1–4

| Gate | Verificación | Comando / Evidencia | Estado |
|---|---|---|---|
| **Gate 1 (Lint & Format)** | Ruff lint + format check | `uv run --directory backend ruff check .` (`All checks passed!`) & `uv run --directory backend ruff format --check .` (`33 files already formatted`) | PASS |
| **Gate 2 (Typecheck)** | Mypy strict (`pydantic.mypy`) | `uv run --directory backend mypy app` (`Success: no issues found in 24 source files`) | PASS |
| **Gate 3 (Seguridad & No-DB-Diff)** | Auditoría anti-bypass RLS + Alembic schema check | `Select-String` en `backend/app/**/*.py` + `uv run --directory backend alembic check` (`No new upgrade operations detected.`) | PASS |
| **Gate 4 (Tests en VERDE)** | Suite completa unitaria + integración | `uv run --directory backend pytest -q` (`47 passed, 3 warnings in 20.28s`, `95%` coverage) | PASS |

### Auditoría Anti-Bypass RLS (Detalle Gate 3)

- **Hallazgo previo en `backend/app/core/config.py:19`:** La coincidencia de la cadena `service_role` corresponde exclusivamente a un comentario restrictivo:
  `# Supabase Auth (prohibido usar service_role en flujos de usuario).`
- **Verificación en flujos de usuario (`app/modules/auth/`, `app/core/db.py`, `app/core/security.py`):**
  - `Settings` solo define `supabase_url` y `supabase_anon_key` (sin `service_role_key`).
  - `AuthService._authenticate_supabase` envía `apikey: self._settings.supabase_anon_key`.
  - `app/core/db.py` ejecuta `SET LOCAL ROLE app_api` y `SELECT set_config('app.current_user_id', :user_id, true)` / `SELECT set_config('app.current_business_id', :business_id, true)` en `set_rls_user_context`, `set_rls_business_context`, `get_user_db` y `get_tenant_db`.
  - `AuthRepository` invoca `set_rls_user_context` antes de consultar `business_users`, `set_rls_business_context` antes de consultar `businesses`, y ambos antes de `INSERT INTO businesses ... RETURNING` + `INSERT INTO business_users` en onboarding.
  - No existe ningún uso de `service_role`, `BYPASSRLS` ni `superuser` en el código productivo.

---

## 3. Matriz `Scenario -> test` (`specs/auth-onboarding/spec.md`)

| Requisito | Escenario (`spec.md`) | Archivo y Test | Estado |
|---|---|---|---|
| User Authentication via Login | `Successful login with existing business` | `tests/integration/test_auth_onboarding.py::test_login_success_with_existing_business` | PASS |
| User Authentication via Login | `Successful login requiring onboarding` | `tests/integration/test_auth_onboarding.py::test_login_success_requiring_onboarding` | PASS |
| User Authentication via Login | `Invalid credentials` | `tests/integration/test_auth_onboarding.py::test_login_invalid_credentials_returns_401_without_cookie` | PASS |
| Business Onboarding & IANA TZ | `Successful business onboarding with country timezone resolution` | `tests/integration/test_auth_onboarding.py::test_onboarding_success_with_country_timezone_resolution` | PASS |
| Business Onboarding & IANA TZ | `Successful business onboarding with explicit valid IANA timezone` | `tests/integration/test_auth_onboarding.py::test_onboarding_success_with_explicit_valid_iana_timezone` | PASS |
| Business Onboarding & IANA TZ | `Onboarding with invalid or unrecognized IANA timezone` | `tests/unit/test_auth_schemas.py::test_onboarding_rejects_invalid_or_unrecognized_iana_timezone` (5 casos) | PASS |
| Business Onboarding & IANA TZ | `Onboarding with unsupported or invalid country code` | `tests/unit/test_auth_schemas.py::test_onboarding_rejects_unsupported_or_invalid_country_or_blank_name` (7 casos) | PASS |
| Business Onboarding & IANA TZ | `Unauthenticated onboarding attempt` | `tests/integration/test_auth_onboarding.py::test_onboarding_unauthenticated_returns_401` | PASS |
| Business Onboarding & IANA TZ | `Duplicate business creation attempt` | `tests/integration/test_auth_onboarding.py::test_onboarding_duplicate_business_returns_409` | PASS |
| Business Onboarding & IANA TZ | `Concurrent onboarding requests enforce single business per user` | `tests/integration/test_auth_onboarding.py::test_onboarding_concurrent_requests_enforce_single_business_no_orphans` | PASS |
| Row-Level Security Context Injection | `Login membership lookup uses app current user id without deadlock` | `tests/integration/test_auth_onboarding.py::test_rls_login_membership_lookup_no_deadlock_and_isolates_users` | PASS |
| Row-Level Security Context Injection | `Valid tenant context set on transactional session` | `tests/integration/test_auth_onboarding.py::test_rls_valid_tenant_context_and_cross_tenant_isolation` | PASS |
| Row-Level Security Context Injection | `Request lacking business context blocked from tenant resources` | `tests/integration/test_auth_onboarding.py::test_rls_request_lacking_business_context_blocked` | PASS |
| Row-Level Security Context Injection | `Cross-tenant database isolation enforced under app_api` | `tests/integration/test_auth_onboarding.py::test_rls_valid_tenant_context_and_cross_tenant_isolation` | PASS |

---

## 4. Coherence & Drift Check (`design.md` vs Código)

- **Dependencias (`backend/pyproject.toml`):** `tzdata>=2026.6` presente.
- **Configuración (`backend/app/core/config.py`):** `database_url`, `db_pool_statement_cache_size=0`, `supabase_url`, `supabase_anon_key`, `jwt_secret_key`, `jwt_algorithm="HS256"`, `access_token_expire_minutes=15`, `cookie_name="access_token"`, `cookie_secure=True`. Sin secretos hardcodeados.
- **Esquemas (`backend/app/modules/auth/schemas.py`):** `COUNTRY_TIMEZONES` (12 países ISO alpha-2), `_validate_iana_timezone` con `ZoneInfo` y `<= 50` chars, `LoginRequest`, `UserPayload`, `BusinessSummary`, `LoginResponse`, `OnboardingRequest`, `BusinessResponse`, `ErrorResponse`. Sin fugas de campos sensibles.
- **Seguridad y Sesión (`backend/app/core/security.py`, `backend/app/core/db.py`):** JWT con claims `sub`, `email`, `business_id`, `role`, `iat`, `exp`; cookie `HttpOnly; SameSite=Strict; Path=/`; `get_current_user` (`401`), `get_current_tenant` (`403` si `business_id is None`), `get_user_db` y `get_tenant_db`.
- **Endpoints (`backend/app/modules/auth/router.py`, `backend/app/main.py`):** `POST /api/v1/auth/login` (`200`/`401`/`422`) y `POST /api/v1/auth/onboarding` (`201`/`401`/`403`/`409`/`422`) montados bajo `/api/v1`.

---

## Evidencia contra la base/entorno

- `uv run --directory backend alembic current` → `e4a7c2b91f03 (head)`.
- `uv run --directory backend alembic check` → `No new upgrade operations detected.` (0 drift entre `models.py` inmutable y la base PostgreSQL local).
- Los tests de integración ejecutaron transacciones reales contra PostgreSQL 17 bajo `SET LOCAL ROLE app_api`, verificando `current_user = 'app_api'`, `app.current_user_id`, `app.current_business_id`, aislamiento entre `Tenant A` y `Tenant B`, y rollback sin huérfanos ante concurrencia (`SQLSTATE 23505`).

---

## Punto ciego

- **Supabase Auth externo mockeado en integración:** Las llamadas HTTP a `POST /auth/v1/token?grant_type=password` se interceptaron mediante `httpx.AsyncHTTPTransport.handle_async_request` en `tests/integration/test_auth_onboarding.py` (`TEST_SUPABASE_URL = "https://supabase.test.local"`). No se ejecutó prueba contra una instancia viva de GoTrue/Supabase Auth en este entorno.
- **Dependencia `get_user_db`:** `get_user_db` en `backend/app/core/db.py` (líneas 65–72) no tiene consumidor directo en el router actual (login y onboarding gestionan sus transacciones en `AuthRepository`) y figura sin cobertura directa en el reporte (`89%` en `db.py`), aunque delega en `set_rls_user_context` que sí está cubierto.

---

## Hallazgos

- **CRITICAL:** Ninguno.
- **WARNING:** Ninguno.
- **SUGGESTION:**
  1. Configurar `asyncio_default_fixture_loop_scope = "function"` en `backend/pyproject.toml` (`[tool.pytest.ini_options]`) para eliminar el `PytestDeprecationWarning` de `pytest-asyncio`.
  2. Migrar `cookies=...` por petición a nivel de cliente en `test_auth_onboarding.py` en futuros refactors para evitar el `DeprecationWarning` de `httpx`.
