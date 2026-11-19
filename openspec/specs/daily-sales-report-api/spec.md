## ADDED Requirements

### Requirement: Daily Sales Summary Aggregation in Business Local Timezone
The system SHALL expose `GET /api/v1/reports/daily` accepting an optional ISO 8601 `date` query parameter (`YYYY-MM-DD`, defaulting to the current local date in the authenticated business's IANA `timezone`) and aggregating sales for the authenticated `business_id` matching `(created_at AT TIME ZONE b.timezone)::date = :fecha`, returning HTTP 200 OK with `date`, `timezone`, `total_sales`, `transactions_count`, `total_cost`, `gross_margin`, `margin_percentage`, and `payment_breakdown` (`cash`, `card`, `transfer`) without join fan-out duplication across `sale_items` and `payments`.

#### Scenario: Daily report aggregates sales, costs, margin, and payment breakdown for a day with sales
- **GIVEN** an authenticated owner session whose business has multiple completed sales on the queried local date, including a sale with multiple `sale_items` rows and combined `payments` across `'cash'`, `'card'`, and `'transfer'`
- **WHEN** the owner calls `GET /api/v1/reports/daily?date=YYYY-MM-DD`
- **THEN** the system SHALL return HTTP 200 OK with exact `total_sales`, exact `transactions_count`, itemized `payment_breakdown` (`cash`, `card`, `transfer`), exact `total_cost`, `gross_margin`, and `margin_percentage` without multiplying totals by the Cartesian product of items and payments

#### Scenario: Sales near UTC midnight are grouped strictly by the business IANA timezone
- **GIVEN** a business configured with a non-UTC IANA timezone (such as `America/Argentina/Buenos_Aires`, UTC-3) having sales recorded at UTC timestamps immediately before local midnight (`02:30:00Z` on the target UTC date), at local midnight (`03:00:00Z`), immediately before next local midnight (`02:59:59Z` of the following UTC date), and at next local midnight (`03:00:00Z` of the following UTC date)
- **WHEN** the owner calls `GET /api/v1/reports/daily` for that target local date
- **THEN** the system SHALL include strictly the sales whose local timestamp in `businesses.timezone` falls on the target local date and exclude sales belonging to adjacent local dates

#### Scenario: Omitted date query parameter defaults to current local date in business timezone
- **GIVEN** an authenticated owner session for a business with a configured IANA `timezone` and sales recorded on the current local date in that timezone
- **WHEN** the owner calls `GET /api/v1/reports/daily` without a `date` query parameter
- **THEN** the system SHALL resolve the current date using `businesses.timezone` and return HTTP 200 OK containing that resolved local `date`, `timezone`, and the corresponding daily metrics

---

### Requirement: Zero-Value Day Handling and Division-by-Zero Protection
When the authenticated business has zero sales on the queried local date, the system SHALL return HTTP 200 OK with zero-initialized numeric values (`"0.00"` for all monetary and percentage strings and `0` for `transactions_count`), protecting profitability calculations against division by zero and returning zero `null` fields.

#### Scenario: Day without sales returns zero totals without nulls or division by zero
- **GIVEN** an authenticated owner session whose business has no sales on the queried local date (including when sales exist on other dates)
- **WHEN** the owner calls `GET /api/v1/reports/daily?date=YYYY-MM-DD`
- **THEN** the system SHALL return HTTP 200 OK with `transactions_count = 0`, `total_sales = "0.00"`, `total_cost = "0.00"`, `gross_margin = "0.00"`, `margin_percentage = "0.00"`, and `payment_breakdown = { "cash": "0.00", "card": "0.00", "transfer": "0.00" }` with no `null` attributes and no division-by-zero errors

---

### Requirement: Exact Decimal Cost, Gross Margin, and Profitability Precision
The system SHALL compute `total_cost` using exact `Decimal` summation of `quantity * unit_cost` from frozen `sale_items` snapshots (independent of subsequent `products.cost_price` modifications), quantizing `total_cost` to two decimal places (`ROUND_HALF_UP`), SHALL compute `gross_margin = total_sales - total_cost` in `Decimal`, and SHALL compute `margin_percentage = ((gross_margin / total_sales) * 100)` quantized to two decimal places (`ROUND_HALF_UP`) whenever `total_sales > 0`, serializing all monetary and percentage values as two-decimal strings without floating-point drift.

#### Scenario: Frozen unit_cost snapshot and fractional quantities preserved after product cost changes
- **GIVEN** a business with sales containing fractional `quantity` and `unit_cost` values (including `unit_cost = "0.00"`) whose referenced products subsequently had `products.cost_price` modified
- **WHEN** the owner calls `GET /api/v1/reports/daily` for that sale date
- **THEN** the system SHALL compute `total_cost` strictly from `sale_items.quantity * sale_items.unit_cost`, compute `gross_margin` as `total_sales - total_cost`, and serialize all amounts and `margin_percentage` as exact two-decimal strings

#### Scenario: Negative gross margin and negative profitability serialized accurately
- **GIVEN** a business with a sale on the queried date where `total_cost` exceeds `total_sales`
- **WHEN** the owner calls `GET /api/v1/reports/daily` for that date
- **THEN** the system SHALL return HTTP 200 OK with signed negative two-decimal strings for `gross_margin` and `margin_percentage` without clamping to zero

---

### Requirement: Query Parameter Validation and Uniform Error Format
The system SHALL strictly validate the optional `date` query parameter as an ISO 8601 calendar date (`YYYY-MM-DD`) within bounded operational range (`1970-01-01` to `2100-12-31`), rejecting empty strings, invalid formats, non-existent calendar dates, timestamps, out-of-range dates, and NUL bytes (`\x00`) with HTTP 422 Unprocessable Content conforming to `ErrorResponse` (`{ "code": "VALIDATION_ERROR", "message", "details" }`) before querying the database.

#### Scenario: Malformed, empty, out-of-bounds, or NUL-byte date query rejected with 422
- **GIVEN** an authenticated owner session
- **WHEN** the client calls `GET /api/v1/reports/daily` with `date` set to `""`, `"not-a-date"`, `"19-11-2026"`, `"2026-02-30"`, `"2026-11-19T12:00:00"`, `"1969-12-31"`, `"2101-01-01"`, or containing `\x00`
- **THEN** the system SHALL reject the request with HTTP 422 (`ErrorResponse` with `code = "VALIDATION_ERROR"`, `message`, and `details`) without executing database queries

---

### Requirement: Authentication, Owner-Only Authorization, and Multi-Tenant RLS Isolation
The system SHALL enforce session authentication (`401 UNAUTHENTICATED`), active business association (`403 ONBOARDING_REQUIRED`), owner-only access (`403 FORBIDDEN` for non-owner roles before executing database queries), transactional PostgreSQL RLS isolation (`SET LOCAL ROLE app_api`, `app.current_user_id`, and `app.current_business_id` derived exclusively from the JWT), and HTTP 404 Not Found (`BUSINESS_NOT_FOUND`) when the authenticated business does not exist under RLS.

#### Scenario: Unauthenticated or onboarding-pending requests rejected with 401 and 403
- **GIVEN** a request lacking a valid `access_token` cookie OR carrying a valid JWT with `business_id = null`
- **WHEN** the client calls `GET /api/v1/reports/daily`
- **THEN** unauthenticated requests SHALL receive HTTP 401 (`code = "UNAUTHENTICATED"`) and onboarding-pending requests SHALL receive HTTP 403 (`code = "ONBOARDING_REQUIRED"`) without executing database queries

#### Scenario: Non-owner role denied access to daily report with 403 Forbidden
- **GIVEN** an authenticated tenant user whose JWT carries `role = "cashier"` and a valid `business_id`
- **WHEN** the user calls `GET /api/v1/reports/daily`
- **THEN** the system SHALL reject the request with HTTP 403 Forbidden (`ErrorResponse` with `code = "FORBIDDEN"`) without executing report queries

#### Scenario: Tenant isolation enforced via RLS excludes other businesses and ignores query business_id
- **GIVEN** business A and business B each having recorded sales on the same local date
- **WHEN** an authenticated owner of business A calls `GET /api/v1/reports/daily` (including when supplying an extraneous `business_id` query parameter targeting business B)
- **THEN** the backend SHALL execute under `app_api` with `app.current_business_id = <business_a>`, ignore any client-supplied `business_id`, and return strictly business A's totals without leaking business B's data

#### Scenario: Non-existent business under RLS returns 404 Not Found
- **GIVEN** an authenticated owner JWT referencing a `business_id` that does not exist in `businesses`
- **WHEN** the client calls `GET /api/v1/reports/daily`
- **THEN** the system SHALL return HTTP 404 Not Found with `ErrorResponse` (`code = "BUSINESS_NOT_FOUND"`)

---

### Requirement: OpenAPI Contract Documentation and Synchronization
The system SHALL register the reports router under `/api/v1` with OpenAPI metadata (`tags=["reports"]`, query parameter `date`, `200` schema `DailyReportResponse` with `PaymentMethodBreakdown`, and error schemas `401`, `403`, `404`, `422` using `ErrorResponse`), keeping the exported static contract `docs/api/openapi.json` synchronized with the FastAPI application.

#### Scenario: Daily report route and schemas documented in OpenAPI and static export
- **GIVEN** the FastAPI application
- **WHEN** requesting `GET /openapi.json` or verifying the static OpenAPI export
- **THEN** the OpenAPI specification SHALL expose `GET /api/v1/reports/daily` tagged `reports` with query parameter `date`, response schemas `DailyReportResponse`, `PaymentMethodBreakdown`, and `ErrorResponse`, and status codes `200`, `401`, `403`, `404`, and `422`
