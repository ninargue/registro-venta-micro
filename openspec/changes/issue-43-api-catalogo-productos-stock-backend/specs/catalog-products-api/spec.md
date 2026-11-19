## ADDED Requirements

### Requirement: Product Creation via Catalog Endpoint
The system SHALL expose `POST /api/v1/catalog/products` to allow an authenticated business owner to create a catalog product associated exclusively with the `business_id` from the session JWT, returning HTTP 201 Created with the persisted product representation including server-generated `id`, `is_active`, `created_at`, and `updated_at`, and returning HTTP 409 Conflict when a non-null `code` already exists within the same business.

#### Scenario: Successful product creation with all attributes
- **GIVEN** an authenticated owner session belonging to an onboarded business
- **WHEN** the owner sends `POST /api/v1/catalog/products` with trimmed non-empty `code`, `name`, positive `sale_price`, non-negative `cost_price`, and non-negative `stock` as exact decimal strings
- **THEN** the system SHALL execute the insert inside a tenant-scoped RLS transaction, store the row with the session `business_id` and `is_active = true`, and return HTTP 201 Created with the created product including `sale_price`, `cost_price`, and `stock` serialized with two decimal places

#### Scenario: Successful product creation with defaults for optional fields
- **GIVEN** an authenticated owner session belonging to an onboarded business
- **WHEN** the owner sends `POST /api/v1/catalog/products` providing only `name` and `sale_price` (omitting `code`, `cost_price`, and `stock`)
- **THEN** the system SHALL persist the product with `code = null`, `cost_price = "0.00"`, `stock = "0.00"`, and `is_active = true`, returning HTTP 201 Created

#### Scenario: Multiple products without code allowed in the same business
- **GIVEN** an authenticated owner session for a business that already has a product with `code = null`
- **WHEN** the owner creates another product in the same business with `code` omitted or `null`
- **THEN** the system SHALL create the second product successfully and return HTTP 201 Created

#### Scenario: Same product code allowed across distinct businesses
- **GIVEN** business A already owns a product with a specific `code`
- **WHEN** an authenticated owner of business B creates a product via `POST /api/v1/catalog/products` with the same `code`
- **THEN** the system SHALL persist business B's product under business B's tenant context and return HTTP 201 Created

#### Scenario: Duplicate non-null product code in the same business returns 409 Conflict
- **GIVEN** an authenticated owner session for a business that already has a product with a non-null `code`
- **WHEN** the owner sends `POST /api/v1/catalog/products` using the same `code` (including with surrounding whitespace that trims to the same value)
- **THEN** the system SHALL catch the unique constraint violation (`uq_products_business_id_code`, SQLSTATE `23505`), roll back the transaction cleanly without leaving corrupted session state, and return HTTP 409 Conflict with `ErrorResponse` (`code = "PRODUCT_CODE_ALREADY_EXISTS"`)

---

### Requirement: Strict Decimal Precision and Domain Input Validation
The system SHALL validate product inputs in Pydantic v2 using `decimal.Decimal` for `sale_price`, `cost_price`, and `stock` (strictly rejecting Python `float`, `bool`, `NaN`, `Infinity`, values exceeding `numeric(12,2)` bounds, and values with more than two decimal places), enforcing `sale_price > 0`, `cost_price >= 0`, `stock >= 0` on creation, non-empty trimmed `name` (`1..150` chars), optional non-empty trimmed `code` (`1..50` chars when not `null`), and rejecting NUL bytes (`\x00`) across all string inputs and query parameters with HTTP 422 Unprocessable Content (`code = "VALIDATION_ERROR"`).

#### Scenario: Exact Decimal persistence and string serialization without floating-point drift
- **GIVEN** an authenticated owner session
- **WHEN** the owner creates a product with `sale_price = "19.99"`, `cost_price = "0.10"`, and `stock = "0.20"` (or integer values normalized to two decimals)
- **THEN** the system SHALL validate and persist exact `Decimal` values in `numeric(12,2)` and serialize them in JSON responses as two-decimal strings (`"19.99"`, `"0.10"`, `"0.20"`) without floating-point representation drift

#### Scenario: Rejection of float values and excessive decimal places on monetary and stock fields
- **GIVEN** an authenticated owner session
- **WHEN** a request or schema instantiation supplies a raw `float` value, a boolean, `NaN`/`Infinity`, or a decimal string with more than two decimal places (e.g. `"12.345"`) for `sale_price`, `cost_price`, or `stock`
- **THEN** Pydantic v2 validation SHALL reject the input before database execution and return HTTP 422 with `ErrorResponse` (`code = "VALIDATION_ERROR"`)

#### Scenario: Rejection of invalid prices, negative initial stock, or numeric overflow
- **GIVEN** an authenticated owner session
- **WHEN** the client submits `sale_price <= 0` (`"0.00"` or `"-1.00"`), `cost_price < 0`, initial `stock < 0`, explicit `null` for `cost_price` or `stock`, or any amount exceeding `"9999999999.99"`
- **THEN** Pydantic v2 validation SHALL reject the payload and return HTTP 422 with `ErrorResponse` (`code = "VALIDATION_ERROR"`)

#### Scenario: Rejection of blank name, blank code, NUL bytes, or oversized strings
- **GIVEN** an authenticated session
- **WHEN** the client submits whitespace-only `name`, whitespace-only non-null `code` (`""` or `"   "`), `name` exceeding 150 characters, `code` exceeding 50 characters, or `\x00` inside `name`, `code`, or search parameter `q`
- **THEN** the system SHALL reject the request with HTTP 422 (`code = "VALIDATION_ERROR"`) without executing database queries

---

### Requirement: Catalog Listing, Deterministic Ordering, and Text Search
The system SHALL expose `GET /api/v1/catalog/products` returning a paginated envelope `{ "items", "total", "limit", "offset" }` scoped to the authenticated tenant, ordered deterministically by `name ASC, id ASC`, supporting optional case-insensitive text search `q` across `name` and `code` with SQL `LIKE`/`ILIKE` wildcard escaping, optional `include_inactive` boolean filtering (default `false`), bounded `limit` (`1..200`, default `50`) and `offset` (`>= 0`, default `0`), and preserving exact signed `Decimal` stock values (including transient negative stock balances from counter sales).

#### Scenario: List active products ordered deterministically by name and id
- **GIVEN** an authenticated tenant with multiple active products including negative transient stock from sales and products with `code = null`
- **WHEN** the client calls `GET /api/v1/catalog/products` without filters
- **THEN** the system SHALL return HTTP 200 OK with `{ items, total, limit, offset }`, containing only active products of that tenant ordered by `name ASC, id ASC`, preserving exact two-decimal strings including negative `stock` values (e.g. `"-1.50"`)

#### Scenario: Text search matches product name or code case-insensitively with SQL wildcard escaping
- **GIVEN** an authenticated tenant with products whose names or codes contain mixed-case text and literal `%` or `_` characters (e.g. `"Descuento 10%"` and `"SKU_01"`)
- **WHEN** the client calls `GET /api/v1/catalog/products?q=<text>` matching either a partial `name` or partial `code` (including literal `%` or `_`)
- **THEN** the system SHALL return HTTP 200 OK with only the active products whose `name` or `code` contains the literal escaped substring case-insensitively, along with the matching `total` count

#### Scenario: Empty or whitespace-only search query returns full active catalog and supports pagination
- **GIVEN** an authenticated tenant with more products than the requested page `limit`
- **WHEN** the client calls `GET /api/v1/catalog/products?q=%20%20&limit=2&offset=2`
- **THEN** the system SHALL ignore the blank search filter, return HTTP 200 OK with the corresponding slice of active products, exact `total` count of active products, and echoed `limit` and `offset`

#### Scenario: Inactive products hidden by default and revealed when include_inactive is true
- **GIVEN** an authenticated tenant with both active (`is_active = true`) and deactivated (`is_active = false`) products
- **WHEN** the client calls `GET /api/v1/catalog/products` with default parameters and then with `include_inactive=true`
- **THEN** the default response SHALL exclude inactive products from `items` and `total`, while `include_inactive=true` SHALL return both active and inactive products of that tenant

---

### Requirement: Authentication, Role Authorization, and Multi-Tenant RLS Isolation
The system SHALL protect `GET /api/v1/catalog/products` and `POST /api/v1/catalog/products` with session authentication (`401 UNAUTHENTICATED`), active tenant enforcement (`403 ONBOARDING_REQUIRED`), owner-only authorization on creation (`403 FORBIDDEN` for non-owner roles), cost redaction (`cost_price = null`) on listing for non-owner roles, and transactional PostgreSQL RLS isolation (`SET LOCAL ROLE app_api`, `app.current_user_id`, and `app.current_business_id`) ignoring any client-supplied `business_id`.

#### Scenario: Unauthenticated or onboarding-pending requests rejected with 401 and 403
- **GIVEN** a client without a valid `access_token` cookie OR a client carrying a valid JWT with `business_id = null`
- **WHEN** the client calls `GET /api/v1/catalog/products` or `POST /api/v1/catalog/products`
- **THEN** unauthenticated requests SHALL receive HTTP 401 (`code = "UNAUTHENTICATED"`) and onboarding-pending requests SHALL receive HTTP 403 (`code = "ONBOARDING_REQUIRED"`) without executing catalog queries

#### Scenario: Product creation restricted to owner role with 403 for cashier
- **GIVEN** an authenticated tenant user whose JWT carries `role = "cashier"` and a valid `business_id`
- **WHEN** the user submits a valid payload to `POST /api/v1/catalog/products`
- **THEN** the system SHALL reject the request with HTTP 403 Forbidden (`ErrorResponse` with `code = "FORBIDDEN"`) before inserting into `products`

#### Scenario: Listing redacts cost_price to null for cashier while exposing it to owner
- **GIVEN** a business with existing products having non-zero `cost_price`
- **WHEN** a user with `role = "cashier"` calls `GET /api/v1/catalog/products` versus a user with `role = "owner"`
- **THEN** both SHALL receive HTTP 200 OK with the tenant's products, where `cost_price` is returned as `null` for `cashier` and as the exact decimal string for `owner`

#### Scenario: Tenant isolation enforced via RLS prevents reading other business products and ignores body business_id
- **GIVEN** business A and business B each have distinct products in `products`
- **WHEN** an authenticated owner of business A queries `GET /api/v1/catalog/products` or attempts `POST /api/v1/catalog/products` including business B's UUID in a body field `business_id`
- **THEN** `GET` SHALL run under `app_api` with `app.current_business_id = <business_a>` and return zero products from business B, and `POST` SHALL ignore the body `business_id` and persist the new product strictly under `<business_a>`

---

### Requirement: OpenAPI Contract Documentation and Uniform Error Schema
The system SHALL register the catalog router under `/api/v1` with OpenAPI metadata (`tags=["catalog"]`, request/response schemas, query parameters, and error response models `401`, `403`, `409`, `422`), and SHALL ensure all HTTP and validation error responses from catalog endpoints conform to `ErrorResponse` (`{ "code", "message", "details" }`).

#### Scenario: Catalog routes and Decimal schemas documented in OpenAPI schema
- **GIVEN** the running FastAPI application
- **WHEN** requesting `GET /openapi.json`
- **THEN** the OpenAPI document SHALL expose paths `/api/v1/catalog/products` for `get` and `post`, define schemas for product creation, product response, paginated product list, and `ErrorResponse`, and document status codes `200`, `201`, `401`, `403`, `409`, and `422`

#### Scenario: All catalog errors conform to uniform ErrorResponse format
- **GIVEN** any invalid payload (`422`), unauthenticated call (`401`), unauthorized role/onboarding (`403`), or duplicate product code (`409`) on `/api/v1/catalog/products`
- **WHEN** the backend returns the error response
- **THEN** the JSON body SHALL contain exactly the top-level keys `code`, `message`, and `details` without FastAPI's default `detail` wrapper
