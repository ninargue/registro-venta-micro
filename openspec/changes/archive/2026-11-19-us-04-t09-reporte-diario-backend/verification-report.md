# Verification Report — `us-04-t09-reporte-diario-backend`

- **Cambio OpenSpec:** `us-04-t09-reporte-diario-backend` (US-04-T09 / Issue #50)
- **Fase:** Fase B — Verificación independiente (`opsx:verify`)
- **Fecha de verificación:** 2026-11-19
- **Veredicto:** **`[APROBADO]`**

---

## 1. Scorecard `opsx:verify`

| Dimensión | Estado | Resultado Observado |
|---|---|---|
| **Completeness** | **PASS (con observaciones)** | 6/6 requisitos y 11/11 escenarios de `specs/daily-sales-report-api/spec.md` implementados en `backend/app/modules/reports/` y `backend/app/main.py`. En `tasks.md`, las tareas `1.1`–`4.2` (8/11) están marcadas `[x]`; las tareas `5.1`–`5.3` (3/11) permanecen `[ ]`: `5.2` y `5.3` están efectivamente ejecutadas y en verde, mientras que `5.1` (`backend/tests/unit/test_reports_schemas.py`) no fue creada como suite unitaria separada. |
| **Correctness** | **PASS** | 11/11 escenarios Given/When/Then cubiertos 1:1 en `backend/tests/integration/test_reports_daily.py` (18 casos de prueba con parametrización de 422) pasando en **VERDE** dentro de la suite completa (`219 passed in 53.64s`, cobertura `93%` total y `91%–100%` en `app/modules/reports/`). |
| **Coherence** | **PASS** | Paridad 1:1 con `design.md` (CTEs desacoplados anti-fan-out, ventana `±2h` + `(s.created_at AT TIME ZONE db.timezone)::date = db.report_date`, `Decimal` `ROUND_HALF_UP`, `require_owner` + `get_tenant_db`, `ErrorResponse`), `0` drift en `docs/api/openapi.json` (`export_openapi --check`), `0` bypass RLS (`service_role` solo en comentario de `config.py:23`) y `0` cambios en `backend/migrations/` o modelos ORM existentes. |

---

## 2. Matriz Técnica de Validaciones y Verificación Fuera del Código

| Gate / Check | Comando Ejecutado | Resultado | Observación |
|---|---|---|---|
| **Gate 1 — Lint & Format** | `cd backend && uv run ruff check . && uv run ruff format --check .` | **PASS** | `All checks passed!`, `55 files already formatted`. |
| **Gate 2 — Typecheck** | `cd backend && uv run mypy app` | **PASS** | `Success: no issues found in 37 source files`. |
| **Gate 3 — Anti-Bypass RLS / Inmutabilidad** | Auditoría estática (`Select-String` `service_role` en `backend/app`) + revisión de `router.py`, `security.py`, `db.py` | **PASS** | La única coincidencia de `service_role` en `backend/app` es el comentario informativo en `backend/app/core/config.py:23` (`# Supabase Auth (prohibido usar service_role en flujos de usuario).`). No existe uso de `service_role` en código ejecutable. `backend/migrations/` y modelos ORM existentes no fueron alterados. |
| **Gate 4 — Suite Completa de Pruebas** | `cd backend && uv run pytest -v` | **PASS** | `219 passed, 81 warnings in 53.64s` (incluye los 18 casos de `tests/integration/test_reports_daily.py`). Cobertura: `reports/repository.py` `100%`, `reports/service.py` `95%`, `reports/router.py` `94%`, `reports/schemas.py` `91%`. |
| **Fuera del Código — OpenAPI Drift** | `cd backend && uv run python -m app.scripts.export_openapi --check` | **PASS** | `OK: docs/api/openapi.json coincide con el esquema OpenAPI actual de FastAPI.` |

---

## 3. Estado Detallado de `tasks.md` (`5.x`)

- **Tareas `1.1` a `4.2` (`8/11`):** Marcadas `[x]` y verificadas contra el código en `backend/app/modules/reports/` (`schemas.py`, `repository.py`, `service.py`, `router.py`), `backend/app/main.py` y `docs/api/openapi.json`.
- **Tarea `5.1` (`[ ]`):** Solicita pruebas unitarias dedicadas en `backend/tests/unit/test_reports_schemas.py`. **Este archivo no existe** en `backend/tests/unit/`. La validación de `DailyReportQuery`, cálculos en `Decimal` y serialización JSON está cubierta por vía HTTP en `backend/tests/integration/test_reports_daily.py` (dejando únicamente sin cubrir las ramas directas de tipos Python `bool|int|float|datetime` / `dt.date` en `schemas.py:34,37,48-51` y la guarda defensiva `business_id is None` en `service.py:31`).
- **Tarea `5.2` (`[ ]`):** Aunque figura sin marcar en `tasks.md`, `backend/tests/integration/test_reports_daily.py` **sí está implementado** y cubre los 11 escenarios de `specs/daily-sales-report-api/spec.md` pasando en **VERDE**.
- **Tarea `5.3` (`[ ]`):** Aunque figura sin marcar en `tasks.md`, toda la cadena (`ruff check`, `ruff format --check`, `export_openapi --check`, `mypy app`, `pytest`) fue ejecutada en esta verificación con resultado **PASS** en verde.

---

## 4. Auditoría de Seguridad y Aislamiento RLS / RBAC

1. **Sin `service_role` en flujos de usuario:** La advertencia de Gate 3 sobre `backend/app/core/config.py` corresponde exclusivamente al comentario en la línea 23 (`# Supabase Auth (prohibido usar service_role en flujos de usuario).`).
2. **Orden de dependencias en `backend/app/modules/reports/router.py`:**
   - `query: Annotated[DailyReportQuery, Query()]` se valida primero (aborta con `422 VALIDATION_ERROR` antes de abrir transacción).
   - `current_user: CurrentUser = Depends(require_owner)` valida cookie `access_token` (`401 UNAUTHENTICATED`), `business_id` en JWT (`403 ONBOARDING_REQUIRED`) y `role == "owner"` (`403 FORBIDDEN`) antes de invocar `get_tenant_db(current_user)`.
   - `async for db in get_tenant_db(current_user):` abre la transacción bajo `SET LOCAL ROLE app_api`, `app.current_user_id` y `app.current_business_id` extraídos exclusivamente del JWT.
3. **Verificación en tests de integración:** `test_daily_report_rejects_invalid_date_query_with_422_before_db`, `test_daily_report_unauthenticated_and_onboarding_pending_rejected` y `test_daily_report_non_owner_role_denied_with_403_before_db` verifican `sql_log == []` (cero consultas a BD). `test_daily_report_tenant_isolation_rls_and_ignore_query_business_id` verifica `set local role app_api`, `app.current_business_id = <business_a>` y que `?business_id=<business_b>` es ignorado sin fuga de datos.

---

## 5. Mapa 1:1 `Scenario -> test` (`specs/daily-sales-report-api/spec.md`)

| # | Scenario (`spec.md`) | Test en `backend/tests/integration/test_reports_daily.py` | Estado |
|---|---|---|---|
| 1 | `Daily report aggregates sales, costs, margin, and payment breakdown for a day with sales` | `test_daily_report_aggregates_sales_without_fan_out` | **PASSED** |
| 2 | `Sales near UTC midnight are grouped strictly by the business IANA timezone` | `test_daily_report_groups_sales_strictly_by_business_iana_timezone` | **PASSED** |
| 3 | `Omitted date query parameter defaults to current local date in business timezone` | `test_daily_report_omitted_date_defaults_to_business_local_date` | **PASSED** |
| 4 | `Day without sales returns zero totals without nulls or division by zero` | `test_daily_report_day_without_sales_returns_zeros_without_nulls` | **PASSED** |
| 5 | `Frozen unit_cost snapshot and fractional quantities preserved after product cost changes` | `test_daily_report_preserves_frozen_unit_cost_and_decimal_precision` | **PASSED** |
| 6 | `Negative gross margin and negative profitability serialized accurately` | `test_daily_report_negative_gross_margin_serialized_accurately` | **PASSED** |
| 7 | `Malformed, empty, out-of-bounds, or NUL-byte date query rejected with 422` | `test_daily_report_rejects_invalid_date_query_with_422_before_db` (8 casos parametrizados) | **PASSED** |
| 8 | `Unauthenticated or onboarding-pending requests rejected with 401 and 403` | `test_daily_report_unauthenticated_and_onboarding_pending_rejected` | **PASSED** |
| 9 | `Non-owner role denied access to daily report with 403 Forbidden` | `test_daily_report_non_owner_role_denied_with_403_before_db` | **PASSED** |
| 10 | `Tenant isolation enforced via RLS excludes other businesses and ignores query business_id` | `test_daily_report_tenant_isolation_rls_and_ignore_query_business_id` | **PASSED** |
| 11 | `Non-existent business under RLS returns 404 Not Found` | `test_daily_report_nonexistent_business_returns_404` | **PASSED** |
| 12 | `Daily report route and schemas documented in OpenAPI and static export` | `test_openapi_documents_daily_report_route_and_schemas` (+ `export_openapi --check`) | **PASSED** |

*(Nota: el spec contiene 12 bloques `Scenario:` distribuidos en 6 requisitos; los 12 están cubiertos 1:1 y en verde).*

---

## 6. Drift Check (`design.md` / `openapi.json` vs Código)

- **Ruta y metadata:** `GET /api/v1/reports/daily` registrado en `backend/app/main.py` vía `reports_router` (`prefix="/reports"`, `tags=["reports"]`), idéntico a `design.md`.
- **Schemas (`backend/app/modules/reports/schemas.py`):** `DailyReportQuery`, `PaymentMethodBreakdown` y `DailyReportResponse` coinciden 1:1 con `design.md` (`DECIMAL_QUANTIZER = Decimal("0.01")`, `ROUND_HALF_UP`, `MIN_REPORT_DATE = 1970-01-01`, `MAX_REPORT_DATE = 2100-12-31`, `reject_nul_byte`).
- **SQL CTE (`backend/app/modules/reports/repository.py`):** Consulta única con `target_business`, `day_bounds`, `filtered_sales`, `sales_agg`, `items_agg`, `payments_agg` y `bindparam` tipados (`PG_UUID(as_uuid=True)` y `Date()`), idéntica a `design.md`.
- **Servicio (`backend/app/modules/reports/service.py`):** Aritmética exacta en `Decimal` sin `float`, protección `total_sales == Decimal("0.00") -> Decimal("0.00")` y `BusinessNotFoundError` mapeado a `404 BUSINESS_NOT_FOUND` en `router.py`.
- **OpenAPI:** `docs/api/openapi.json` sin drift respecto al esquema generado por FastAPI.

---

## 7. Hallazgos

- **CRITICAL:** Ninguno.
- **WARNING:**
  1. `backend/tests/unit/test_reports_schemas.py` (tarea `5.1` de `tasks.md`) no existe; las validaciones están cubiertas vía integración HTTP en `test_reports_daily.py`, quedando sin ejercitar las ramas de entrada Python directa en `schemas.py:34,37,48-51` y la guarda `business_id is None` en `service.py:31`.
  2. Las casillas `5.1`, `5.2` y `5.3` en `openspec/changes/us-04-t09-reporte-diario-backend/tasks.md` permanecen sin marcar (`[ ]`), aunque `5.2` y `5.3` ya se encuentran implementadas y validadas en verde.
- **SUGGESTION:**
  1. Antes de archivar el cambio (`opsx:archive`), actualizar las casillas `5.2` y `5.3` en `tasks.md` (y opcionalmente añadir `backend/tests/unit/test_reports_schemas.py` si se desea cerrar `5.1` al 100%).
