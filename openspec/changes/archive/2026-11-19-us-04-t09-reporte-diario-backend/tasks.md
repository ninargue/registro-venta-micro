## 1. Tipos de Dominio y DTOs/Schemas de Reportes (consumiendo modelos ORM inmutables)

- [x] 1.1 Verificar disponibilidad de modelos inmutables `Business` (`backend/app/modules/auth/models.py`) y `Sale`, `SaleItem`, `Payment` (`backend/app/modules/sales/models.py`) registrados en `backend/app/db/base.py` sin alterar `backend/migrations/` ni modelos existentes
- [x] 1.2 Implementar esquemas Pydantic v2 en `backend/app/modules/reports/schemas.py` (`DailyReportQuery`, `PaymentMethodBreakdown`, `DailyReportResponse`): validación estricta de `date` (`YYYY-MM-DD`, rango `1970-01-01..2100-12-31`, rechazo de bytes `\x00`, vacíos, timestamps y formatos no ISO), y cuantización `Decimal` a 2 decimales (`ROUND_HALF_UP`) sin uso de `float`

## 2. Repositorio de Reportes bajo RLS

- [x] 2.1 Definir dataclass inmutable `DailySalesAggregate` y crear `ReportsRepository` en `backend/app/modules/reports/repository.py` operando sobre sesión transaccional RLS (`get_tenant_db`)
- [x] 2.2 Implementar `get_daily_aggregate(business_id, report_date)` ejecutando una única consulta SQL con CTEs desacoplados (`target_business`, `day_bounds`, `filtered_sales`, `sales_agg`, `items_agg`, `payments_agg`), parámetros tipados (`UUID` y `Date` para soportar `report_date=None`), ventana acotada `±2h` sobre `ix_sales_business_id_created_at`, predicado exacto `(s.created_at AT TIME ZONE db.timezone)::date = db.report_date`, `SUM(si.quantity * si.unit_cost)` sin fan-out y `COALESCE(..., 0)` para días sin ventas (retornando `None` si el negocio no existe bajo RLS)

## 3. Capa de Servicio de Reportes

- [x] 3.1 Implementar `BusinessNotFoundError` y `ReportsService` en `backend/app/modules/reports/service.py` validando `current_user.business_id` y delegando la agregación al repositorio
- [x] 3.2 Implementar cálculo exacto en `Decimal` (`total_sales`, `total_cost` cuantizado a `0.01` `ROUND_HALF_UP`, `gross_margin = total_sales - total_cost`, `margin_percentage` protegido contra división por cero devolviendo `"0.00"` cuando `total_sales == 0` y admitiendo márgenes negativos) y construcción de `DailyReportResponse` con `PaymentMethodBreakdown` sin campos `null`

## 4. Router FastAPI, Seguridad y Registro en App

- [x] 4.1 Implementar `GET /api/v1/reports/daily` en `backend/app/modules/reports/router.py` con `APIRouter(prefix="/reports", tags=["reports"])`, orden de dependencias `query: Annotated[DailyReportQuery, Query()]`, `current_user: CurrentUser = Depends(require_owner)` antes de `service: ReportsService = Depends(get_reports_service)` (para abortar `401`/`403`/`422` antes de abrir transacción BD), mapeo de `BusinessNotFoundError` a HTTP `404` (`ErrorResponse` `code="BUSINESS_NOT_FOUND"`) y documentación explícita de respuestas `200`/`401`/`403`/`404`/`422`
- [x] 4.2 Registrar `reports_router` en `backend/app/main.py` bajo `prefix="/api/v1"` y regenerar el contrato estático ejecutando `cd backend && uv run python -m app.scripts.export_openapi`

## 5. Pruebas de Dominio, Aislamiento RLS y Validación Determinista

- [x] 5.1 Implementar pruebas de validación de schemas (cobertura consolidada en `backend/tests/integration/test_reports_daily.py`; no existe `tests/unit/test_reports_schemas.py`) cubriendo validación estricta de `DailyReportQuery` (fechas ISO válidas, omisión `None`, rechazo `422` de `\x00`/vacíos/formatos inválidos/timestamps/fuera de rango), cálculos en `Decimal` (margen positivo, costo cero, margen negativo, redondeo `ROUND_HALF_UP`, protección división por cero en `total_sales = 0`) y serialización JSON a dos decimales sin `float` ni `null`
- [x] 5.2 Implementar pruebas de integración y aislamiento RLS en `backend/tests/integration/test_reports_daily.py` cubriendo todos los escenarios de `specs/daily-sales-report-api/spec.md`: día con múltiples ventas e ítems/pagos combinados sin fan-out (`200`), cortes exactos de medianoche en zona horaria del comercio (`America/Argentina/Buenos_Aires` y `America/Santiago` / `Europe/Madrid`), `date` omitido por defecto usando `timezone` del comercio, preservación de `unit_cost` congelado tras editar `products.cost_price`, día sin ventas con ceros sin nulos (`200`), margen negativo (`200`), validación `422` sin consulta BD, `401`/`403 ONBOARDING_REQUIRED`/`403 FORBIDDEN` para `cashier`, aislamiento RLS entre negocios e ignorado de `?business_id=...`, `404 BUSINESS_NOT_FOUND` y contrato OpenAPI `/openapi.json`
- [x] 5.3 Ejecutar validación completa de calidad, contrato y pruebas (`cd backend && uv run ruff check . && uv run ruff format --check . && uv run python -m app.scripts.export_openapi --check && uv run mypy app && uv run pytest`) confirmando 0 cambios en `backend/migrations/` y modelos ORM existentes
