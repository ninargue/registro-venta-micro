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

---

### Requirement: Partial Product Update via Catalog Endpoint
The system SHALL expose `PATCH /api/v1/catalog/products/{product_id}` to allow an authenticated business owner to partially update editable attributes (`code`, `name`, `sale_price`, `cost_price`, `stock`) of an existing product belonging exclusively to the authenticated session's `business_id`, returning HTTP 200 OK with the persisted `ProductResponse`, preserving omitted attributes unchanged (including existing transient negative stock balances when `stock` is omitted), preserving `created_at` and `business_id`, advancing `updated_at`, and returning HTTP 409 Conflict when updating `code` to a non-null value already assigned to another product within the same business.

#### Scenario: Successful partial update of a subset of attributes preserves omitted fields
- **GIVEN** an authenticated owner session for a business owning an existing product with `code = "SKU-001"`, `name = "Yerba Mate"`, `sale_price = "3000.00"`, `cost_price = "2000.00"`, and `stock = "-1.50"`
- **WHEN** the owner sends `PATCH /api/v1/catalog/products/{product_id}` providing only `sale_price = "3500.50"` and `cost_price = "2200.00"` (omitting `code`, `name`, and `stock`)
- **THEN** the system SHALL execute the update inside a tenant-scoped RLS transaction, persist the updated `sale_price` and `cost_price`, leave `code`, `name`, `stock` (`"-1.50"`), `is_active`, `business_id`, and `created_at` unchanged, advance `updated_at`, and return HTTP 200 OK with the updated `ProductResponse` serialized with exact two-decimal strings

#### Scenario: Successful update of all editable attributes including clearing optional code to null
- **GIVEN** an authenticated owner session for a business owning an existing product with a non-null `code` and another product already having `code = null`
- **WHEN** the owner sends `PATCH /api/v1/catalog/products/{product_id}` with trimmed `name`, exact decimal strings for `sale_price`, `cost_price`, and `stock >= 0`, and explicit `"code": null`
- **THEN** the system SHALL update all five attributes setting `code = null` in `products` without uniqueness conflict and return HTTP 200 OK with the updated `ProductResponse`

#### Scenario: Updating a product keeping its own code or matching a code from another business succeeds
- **GIVEN** business A owns product P1 with `code = "ONLY-IN-A"` and business B owns product P2 with `code = "OLD-02"`
- **WHEN** the owner of business A updates P1 sending its own `code = "ONLY-IN-A"` with a new `name`, OR the owner of business B updates P2 sending `code = "ONLY-IN-A"`
- **THEN** both updates SHALL succeed and return HTTP 200 OK because partial uniqueness `uq_products_business_id_code` is scoped per `(business_id, code)`

#### Scenario: Updating code to an existing non-null code in the same business returns 409 Conflict
- **GIVEN** an authenticated owner session for a business owning product P1 (`code = "SKU-001"`) and product P2 (`code = "SKU-002"`)
- **WHEN** the owner sends `PATCH /api/v1/catalog/products/{product_p2_id}` with `code = "  SKU-001  "`
- **THEN** the system SHALL catch the unique constraint violation (`uq_products_business_id_code`, SQLSTATE `23505`), roll back the savepoint cleanly without leaving an aborted session transaction, keep P2's original attributes intact, and return HTTP 409 Conflict with `ErrorResponse` (`code = "PRODUCT_CODE_ALREADY_EXISTS"`)

---

### Requirement: Strict Decimal Precision and Partial Payload Validation on Product Update
The system SHALL validate requests to `PATCH /api/v1/catalog/products/{product_id}` enforcing UUID path parsing for `product_id` and Pydantic v2 schema `ProductUpdate` with strict `decimal.Decimal` validation (`numeric(12,2)` bounds `<= "9999999999.99"`, rejecting raw Python `float`, `bool`, `NaN`, `Infinity`, and more than two decimal places), `sale_price > 0`, `cost_price >= 0`, `stock >= 0`, trimmed non-empty `name` (`1..150` chars), trimmed non-empty non-null `code` (`1..50` chars), NUL byte (`\x00`) rejection, rejection of explicit `null` on non-nullable fields (`name`, `sale_price`, `cost_price`, `stock`), and rejection of empty payloads containing no updatable fields, returning HTTP 422 Unprocessable Content (`code = "VALIDATION_ERROR"`).

#### Scenario: Rejection of float, bool, non-finite decimals, excessive decimal places, and numeric overflow on update
- **GIVEN** an authenticated owner session and an existing product
- **WHEN** the owner sends `PATCH /api/v1/catalog/products/{product_id}` supplying a raw JSON `float`, `bool`, `"NaN"`, `"Infinity"`, more than two decimal places (e.g. `"12.345"`), or an amount exceeding `"9999999999.99"` on `sale_price`, `cost_price`, or `stock`
- **THEN** Pydantic v2 validation SHALL reject the payload before executing database queries and return HTTP 422 with `ErrorResponse` (`code = "VALIDATION_ERROR"`)

#### Scenario: Rejection of non-positive sale_price, negative cost_price, or negative stock on update
- **GIVEN** an authenticated owner session and an existing product
- **WHEN** the owner sends `PATCH /api/v1/catalog/products/{product_id}` with `sale_price <= 0` (`"0.00"` or `"-1.00"`), `cost_price < 0` (`"-0.01"`), or `stock < 0` (`"-0.01"`)
- **THEN** Pydantic v2 validation SHALL reject the payload before executing database queries and return HTTP 422 with `ErrorResponse` (`code = "VALIDATION_ERROR"`)

#### Scenario: Rejection of explicit null on non-nullable fields or empty update payload
- **GIVEN** an authenticated owner session and an existing product
- **WHEN** the owner sends `PATCH /api/v1/catalog/products/{product_id}` with explicit `null` for `name`, `sale_price`, `cost_price`, or `stock`, OR sends an empty JSON body `{}` (or only unpermitted fields without any editable attribute)
- **THEN** Pydantic v2 validation SHALL reject the request with HTTP 422 (`code = "VALIDATION_ERROR"`) without modifying the database record

#### Scenario: Rejection of blank strings, oversized strings, NUL bytes, or invalid product_id UUID
- **GIVEN** an authenticated owner session
- **WHEN** the client sends `PATCH /api/v1/catalog/products/{product_id}` with an invalid UUID in `product_id`, OR sends whitespace-only `name`, whitespace-only non-null `code` (`""` or `"   "`), `name > 150` chars, `code > 50` chars, or `\x00` inside `name` or `code`
- **THEN** the system SHALL reject the request with HTTP 422 (`code = "VALIDATION_ERROR"`) without executing database queries

---

### Requirement: Authorization, Multi-Tenant RLS Isolation, and 404 Semantics on Product Update
The system SHALL protect `PATCH /api/v1/catalog/products/{product_id}` with session authentication (`401 UNAUTHENTICATED`), active tenant onboarding enforcement (`403 ONBOARDING_REQUIRED`), owner-only role authorization (`403 FORBIDDEN` for non-owner roles such as `cashier`), transactional PostgreSQL RLS isolation (`SET LOCAL ROLE app_api`, `app.current_user_id`, `app.current_business_id`), ignoring client-supplied immutable fields (`business_id`, `id`, `created_at`, `updated_at`), and returning HTTP 404 Not Found (`code = "PRODUCT_NOT_FOUND"`) when the product does not exist or belongs to a different business.

#### Scenario: Unauthenticated or onboarding-pending update requests rejected with 401 and 403
- **GIVEN** a client without a valid `access_token` cookie OR a client carrying a valid JWT with `business_id = null`
- **WHEN** the client calls `PATCH /api/v1/catalog/products/{product_id}` with a valid body
- **THEN** unauthenticated requests SHALL receive HTTP 401 (`code = "UNAUTHENTICATED"`) and onboarding-pending requests SHALL receive HTTP 403 (`code = "ONBOARDING_REQUIRED"`) without executing catalog database queries

#### Scenario: Cashier role rejected with 403 Forbidden on product update
- **GIVEN** an authenticated tenant user whose JWT carries `role = "cashier"` and a valid `business_id` owning an existing product
- **WHEN** the cashier sends `PATCH /api/v1/catalog/products/{product_id}` with a valid update payload
- **THEN** the system SHALL reject the request with HTTP 403 Forbidden (`ErrorResponse` with `code = "FORBIDDEN"`) before querying or updating `products`

#### Scenario: Non-existent product_id returns 404 Not Found
- **GIVEN** an authenticated owner session for an onboarded business and a random valid UUID not present in `products`
- **WHEN** the owner sends `PATCH /api/v1/catalog/products/{product_id}` with a valid update payload
- **THEN** the system SHALL execute the update inside the RLS-scoped tenant transaction, match zero rows, and return HTTP 404 Not Found with `ErrorResponse` (`code = "PRODUCT_NOT_FOUND"`)

#### Scenario: Cross-tenant product_id returns 404 Not Found without leaking existence or mutating data
- **GIVEN** business A and business B each exist and business B owns product P_B
- **WHEN** an authenticated owner of business A sends `PATCH /api/v1/catalog/products/{p_b_id}` with a valid update payload
- **THEN** the system SHALL execute under `SET LOCAL ROLE app_api` with `app.current_business_id = <business_a>`, match zero rows under RLS and tenant predicate, return HTTP 404 Not Found (`ErrorResponse` with `code = "PRODUCT_NOT_FOUND"`), and leave product P_B completely unmodified in business B

#### Scenario: Client-supplied business_id or immutable metadata fields in payload are ignored
- **GIVEN** business A owns product P_A and business B exists
- **WHEN** an authenticated owner of business A sends `PATCH /api/v1/catalog/products/{p_a_id}` including `"business_id": "<business_b>"` alongside `"sale_price": "1999.00"`
- **THEN** the system SHALL ignore `"business_id"`, update only `sale_price` on P_A, keep `P_A.business_id == <business_a>`, and return HTTP 200 OK

---

### Requirement: OpenAPI Contract Documentation and Static Synchronization for Product Update
The system SHALL register `PATCH /api/v1/catalog/products/{product_id}` under `tags=["catalog"]` with request schema `ProductUpdate`, response schema `ProductResponse` (`200`), and uniform `ErrorResponse` definitions for status codes `401`, `403`, `404`, `409`, and `422`, and SHALL maintain the versioned static OpenAPI file `docs/api/openapi.json` synchronized via `app.scripts.export_openapi` so `export_openapi --check` passes.

#### Scenario: PATCH catalog route and ProductUpdate schema documented in live and static OpenAPI contracts
- **GIVEN** the FastAPI application and exported `docs/api/openapi.json`
- **WHEN** inspecting `GET /openapi.json` and `docs/api/openapi.json`
- **THEN** both SHALL expose path `/api/v1/catalog/products/{product_id}` for `patch` under tag `catalog` with UUID parameter `product_id`, request schema `ProductUpdate`, response schema `ProductResponse` on `200`, `ErrorResponse` on `401`, `403`, `404`, `409`, and `422`, and `export_openapi --check` SHALL return exit code `0`

#### Scenario: All error responses on product update conform to uniform ErrorResponse format
- **GIVEN** any `401`, `403`, `404`, `409`, or `422` response from `PATCH /api/v1/catalog/products/{product_id}`
- **WHEN** the backend returns the error payload
- **THEN** the JSON body SHALL contain exactly the top-level keys `code`, `message`, and `details` without FastAPI's default `detail` wrapper
