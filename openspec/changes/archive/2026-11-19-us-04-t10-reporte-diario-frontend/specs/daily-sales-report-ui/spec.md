## ADDED Requirements

### Requirement: Daily Sales Report Screen and KPI Cards Display
The frontend application SHALL expose the daily report view at `/reports/daily` and render a semantic main heading (`Reporte Diario de Ventas y Margen`), the active report date (`date`) and business IANA timezone (`timezone`), and four accessible KPI summary cards corresponding 1:1 to `DailyReportResponse` from `GET /api/v1/reports/daily`:
1. **Ventas Totales**: displays formatted `total_sales` (gross revenue without taxes).
2. **Margen Bruto**: displays formatted `gross_margin` and formatted profitability percentage `margin_percentage` (with `%` suffix, preserving negative signs when `gross_margin < 0`).
3. **Costo Mercadería**: displays formatted `total_cost` (`SUM(quantity * unit_cost)`).
4. **Tickets**: displays `transactions_count` (completed sales count).

All monetary strings (`total_sales`, `total_cost`, `gross_margin`) and `margin_percentage` SHALL be formatted deterministically from their exact two-decimal string representation in `DailyReportResponse` without floating-point rounding drift.

#### Scenario: Owner views daily report with sales and positive gross margin (state: ready)
- **GIVEN** the backend responds `200 OK` to `GET /api/v1/reports/daily` with `date = "2026-11-19"`, `timezone = "America/Argentina/Buenos_Aires"`, `total_sales = "30000.00"`, `transactions_count = 3`, `total_cost = "21000.00"`, `gross_margin = "9000.00"`, `margin_percentage = "30.00"`, and `payment_breakdown = { "cash": "15000.00", "card": "10000.00", "transfer": "5000.00" }`
- **WHEN** the user navigates to `/reports/daily`
- **THEN** the view SHALL display the heading `Reporte Diario de Ventas y Margen`, the resolved date `2026-11-19` and timezone `America/Argentina/Buenos_Aires`, the KPI card `Ventas Totales` showing `$30.000,00` (or canonical currency string containing `30.000,00` / `30,000.00`), the KPI card `Margen Bruto` showing `$9.000,00` and `30.00%`, the KPI card `Costo Mercadería` showing `$21.000,00`, and the KPI card `Tickets` showing `3`

#### Scenario: Owner views daily report with negative gross margin (state: ready)
- **GIVEN** the backend responds `200 OK` to `GET /api/v1/reports/daily` with `total_sales = "1000.00"`, `transactions_count = 1`, `total_cost = "1250.00"`, `gross_margin = "-250.00"`, and `margin_percentage = "-25.00"`
- **WHEN** the user views `/reports/daily`
- **THEN** the `Margen Bruto` KPI card SHALL display the signed negative gross margin (`-$250,00` / `-250.00`) and signed negative profitability (`-25.00%`) without clamping to zero

---

### Requirement: Payment Method Breakdown Display
The daily report view SHALL render an accessible payment method breakdown section (`Desglose por Medio de Pago`) presenting a semantic table or description list with rows for the three canonical payment methods defined in `PaymentMethodBreakdown`:
- **Efectivo** (`payment_breakdown.cash`)
- **Tarjeta** (`payment_breakdown.card`)
- **Transferencia** (`payment_breakdown.transfer`)

Each row SHALL display the payment method label, the formatted monetary amount, and its percentage share of `total_sales` quantized to two decimal places (or `0.00%` when `total_sales` is `"0.00"`).

#### Scenario: Payment method breakdown renders amounts and proportions for all three methods
- **GIVEN** `GET /api/v1/reports/daily` returns `total_sales = "30000.00"` and `payment_breakdown = { "cash": "15000.00", "card": "10000.00", "transfer": "5000.00" }`
- **WHEN** the report is rendered in `ready` state
- **THEN** the `Desglose por Medio de Pago` region SHALL display `Efectivo` with `$15.000,00` (`50.00%`), `Tarjeta` with `$10.000,00` (`33.33%`), and `Transferencia` with `$5.000,00` (`16.67%`)

---

### Requirement: Zero-Sales Day Empty State Without Nulls or Division-by-Zero
When `GET /api/v1/reports/daily` returns a day without sales (`transactions_count === 0` and monetary values `"0.00"`), the view SHALL render the `empty` state banner (`Sin ventas registradas en la fecha seleccionada`) while keeping the KPI cards and payment method breakdown visible with zero-formatted values (`$0,00`, `0.00%`, `0`), never rendering `NaN`, `Infinity`, `null`, or `undefined`.

#### Scenario: Day without sales displays empty state notice and zero KPIs (state: empty)
- **GIVEN** `GET /api/v1/reports/daily` returns `200 OK` with `date = "2026-11-19"`, `timezone = "America/Argentina/Buenos_Aires"`, `transactions_count = 0`, `total_sales = "0.00"`, `total_cost = "0.00"`, `gross_margin = "0.00"`, `margin_percentage = "0.00"`, and `payment_breakdown = { "cash": "0.00", "card": "0.00", "transfer": "0.00" }`
- **WHEN** the user views `/reports/daily`
- **THEN** the view SHALL display the empty-day message `Sin ventas registradas en la fecha seleccionada`, render `Ventas Totales` as `$0,00`, `Margen Bruto` as `$0,00` (`0.00%`), `Costo Mercadería` as `$0,00`, `Tickets` as `0`, and each payment method (`Efectivo`, `Tarjeta`, `Transferencia`) as `$0,00` (`0.00%`) with no `NaN` or `null` text

---

### Requirement: Date Filter Control in Business Local Timezone
The daily report view SHALL provide an accessible date input labeled `Fecha del reporte` (`YYYY-MM-DD`). On initial load without a `date` URL search parameter, the view SHALL request `GET /api/v1/reports/daily` without the `date` query parameter so the backend resolves the current local date in `businesses.timezone`, and SHALL synchronize the input value with the `date` returned in `DailyReportResponse`. When the user selects a valid `YYYY-MM-DD` date, the view SHALL query `GET /api/v1/reports/daily?date=YYYY-MM-DD` and update the displayed KPIs and breakdown.

#### Scenario: Initial load omits date query parameter and syncs resolved business local date
- **GIVEN** the user opens `/reports/daily` without a pre-selected date
- **WHEN** the view mounts and `GET /api/v1/reports/daily` returns `date = "2026-11-19"` and `timezone = "America/Argentina/Buenos_Aires"`
- **THEN** the initial HTTP request SHALL be sent to `/api/v1/reports/daily` (without `?date=`), and upon response the `Fecha del reporte` input SHALL display `"2026-11-19"`

#### Scenario: Selecting a new date triggers a report query for that date
- **GIVEN** the user is viewing `/reports/daily` loaded for `"2026-11-19"`
- **WHEN** the user changes the `Fecha del reporte` control to `"2026-11-18"`
- **THEN** the client SHALL request `GET /api/v1/reports/daily?date=2026-11-18` and update the KPI cards, payment breakdown, and displayed date to match the `"2026-11-18"` response

---

### Requirement: Accessible Loading and Error States with Retry
The daily report view SHALL expose observable, accessible states for in-flight requests (`loading`) and failed requests (`error` on HTTP `401`, `403`, `404`, `422`, `5xx`, or network failure):
- While fetching, an accessible status indicator (`role="status"`, text `Cargando reporte diario...`) SHALL be rendered.
- When the API returns an `ErrorResponse` (`{ code, message, details }`) or network failure, an accessible alert (`role="alert"`) SHALL display the error message and an interactive button `Reintentar` (`min-height: 48px` touch target) that triggers a fresh query to `GET /api/v1/reports/daily`.

#### Scenario: Loading indicator is announced while daily report request is pending (state: loading)
- **GIVEN** a request to `GET /api/v1/reports/daily` is in flight
- **WHEN** `/reports/daily` is rendered
- **THEN** an element with `role="status"` containing `Cargando reporte diario...` SHALL be present in the document

#### Scenario: API error displays accessible alert with server message and retry action recovers (state: error)
- **GIVEN** `GET /api/v1/reports/daily` initially fails with HTTP `403` and `ErrorResponse` `{ "code": "FORBIDDEN", "message": "Solo el dueño del comercio puede consultar reportes", "details": null }` (or HTTP `500` / `422`)
- **WHEN** `/reports/daily` is rendered and the user clicks the `Reintentar` button after the endpoint recovers with `200 OK`
- **THEN** the view SHALL first render `role="alert"` displaying `Solo el dueño del comercio puede consultar reportes` and the `Reintentar` button, and after clicking `Reintentar` SHALL replace the alert with the loaded daily report KPIs
