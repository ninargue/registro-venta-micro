## MODIFIED Requirements

### Requirement: Atomic Stock Deduction Allowing Transient Negative Balance and ACID Rollback
The system SHALL lock referenced product rows in deterministic `product_id` order (`FOR UPDATE`) and execute atomic stock deduction (`stock = stock - quantity`) inside the sale transaction without rejecting sales when stock is insufficient or becomes negative within `numeric(12,2)` bounds, SHALL prevent deadlocks and lost updates under concurrent crossed-order multi-product sales, and SHALL roll back the entire transaction (sale header, items, payments, and stock updates) on any mid-transaction failure.

#### Scenario: Counter sale succeeds when stock becomes negative
- **GIVEN** an authenticated tenant session and an active product with `stock = "2.00"` (or already negative `"-1.00"`)
- **WHEN** the user submits a valid sale via `POST /api/v1/sales` for `quantity = "3.00"` (or `"2.00"`)
- **THEN** the system SHALL complete the sale with HTTP 201 Created and persist `products.stock = "-1.00"` (or `"-3.00"`) without rejecting the operation

#### Scenario: Concurrent crossed-order multi-item sales complete without deadlocks or lost updates
- **GIVEN** an authenticated tenant with two active products `P1` and `P2`, each having `stock = "10.00"` and `sale_price = "100.00"`
- **WHEN** two concurrent `POST /api/v1/sales` requests with distinct `client_id` values arrive simultaneously with inverted item orderings (`[P1, P2]` and `[P2, P1]`) deducting `"2.00"` and `"3.00"` of each product respectively
- **THEN** the system SHALL acquire product row locks in deterministic ascending `product_id` order, complete both requests with HTTP 201 Created without database deadlocks (`40P01`), and persist exact final stock `"5.00"` on both `P1` and `P2` with zero lost updates

#### Scenario: Transactional rollback restores database state on mid-transaction failure
- **GIVEN** an authenticated tenant session and an active product with `stock = "10.00"`
- **WHEN** an unexpected exception occurs mid-transaction after inserting `sales` or updating `products.stock` (e.g. during `sale_items`, `payments`, or stock persistence)
- **THEN** PostgreSQL SHALL roll back the entire ACID transaction, leaving zero new rows in `sales`, `sale_items`, or `payments` and preserving `products.stock = "10.00"`

---

### Requirement: Idempotent Retry Handling by Business and Client Identifier
The system SHALL guarantee per-business idempotency using `(business_id, client_id)` via early lookup, a post-lock re-lookup executed immediately after acquiring product row locks (`FOR UPDATE`) and before validating product presence, active status, or price/payment reconciliation, and `INSERT ... ON CONFLICT (business_id, client_id) DO NOTHING`. Whenever an existing sale is found for `(business_id, client_id)` at any stage (early lookup, post-lock re-lookup, or after `ON CONFLICT`), the system SHALL compare the incoming `items` (`product_id` and quantized `quantity`) and `payments` (`payment_method` and quantized `amount`) against the persisted sale as order-independent multisets: if they match, it SHALL return HTTP 200 OK with the already persisted sale receipt without creating duplicate rows or re-deducting stock even if catalog prices or `is_active` changed subsequently; if they differ, it SHALL reject the request with HTTP 409 Conflict (`ErrorResponse` with `code = "SALE_ID_CONFLICT"`) without modifying persisted sales or stock, while permitting identical `client_id` values across distinct businesses.

#### Scenario: Sequential retry with identical client_id returns 200 without duplicating records or re-deducting stock
- **GIVEN** an authenticated tenant that already registered a sale for `client_id` when product stock dropped from `"10.00"` to `"8.00"`, even if the product's `sale_price` was later edited or the product was deactivated
- **WHEN** the client retries `POST /api/v1/sales` with the same `client_id`, `items`, and `payments`
- **THEN** the system SHALL return HTTP 200 OK with the previously persisted `SaleResponse`, retain exactly 1 row in `sales` for `(business_id, client_id)`, and keep `products.stock` unchanged at `"8.00"`

#### Scenario: Concurrent retries with identical client_id produce a single sale and single stock deduction
- **GIVEN** an authenticated tenant with an active product having `stock = "10.00"` and a single `client_id`
- **WHEN** two concurrent `POST /api/v1/sales` requests arrive simultaneously with the same `client_id`, `items` (`quantity = "3.00"`), and `payments`
- **THEN** only one request SHALL insert the sale (`201 Created`), the conflicting concurrent request SHALL resolve idempotently before touching stock and return the committed sale (`200 OK`), and `products.stock` SHALL equal `"7.00"` (deducted once)

#### Scenario: Concurrent retry returns 200 OK when catalog price or active status changes while waiting for FOR UPDATE lock
- **GIVEN** an authenticated tenant whose initial sale for `client_id` commits while a concurrent retry with the same `client_id` and identical `items`/`payments` passed early lookup before commit and another catalog transaction updates the product `sale_price` or sets `is_active = false` before the retry acquires `FOR UPDATE`
- **WHEN** the concurrent retry acquires the product lock and executes the post-lock idempotency re-lookup inside its transaction
- **THEN** the system SHALL detect the committed sale before validating `is_active` or payment reconciliation, verify payload equivalence, and return HTTP 200 OK with the committed `SaleResponse` instead of rejecting with `422 PRODUCT_INACTIVE` or `422 PAYMENT_TOTAL_MISMATCH`

#### Scenario: Reusing an existing client_id with different items or payments is rejected with 409 Conflict
- **GIVEN** an authenticated tenant that has already registered (or concurrently commits) a sale for a given `client_id`
- **WHEN** a subsequent or concurrent request uses the same `client_id` with a different `product_id`, different quantized `quantity`, different `payment_method`, different quantized `amount`, or extra/missing lines or payments
- **THEN** the system SHALL reject the conflicting request with HTTP 409 Conflict (`ErrorResponse` with `code = "SALE_ID_CONFLICT"`), preserve the original sale unmodified, and keep product stock unchanged

#### Scenario: Same client_id allowed across distinct businesses without cross-tenant collision
- **GIVEN** business A has already registered a sale with a given `client_id` UUID
- **WHEN** an authenticated user of business B submits `POST /api/v1/sales` using the exact same `client_id` UUID for business B's product
- **THEN** the system SHALL persist business B's sale independently under business B's tenant context and return HTTP 201 Created

---

### Requirement: Strict Decimal Precision, Payment Reconciliation, and Domain Input Validation
The system SHALL validate all monetary and quantity fields in Pydantic v2 using strict `Decimal` (rejecting Python `float`, `bool`, `NaN`, `Infinity`, values exceeding `numeric(12,2)` bounds, and >2 decimal places), require non-empty bounded lists (`1..500` `items` and `1..20` `payments`), restrict `payment_method` to `'cash' | 'card' | 'transfer'`, reject NUL bytes (`\x00`), reject inactive products (`422 PRODUCT_INACTIVE`), reject calculated subtotals/totals `<= 0` or exceeding `numeric(12,2)`, reject per-product aggregated stock deductions exceeding `"9999999999.99"` or resulting stock `(current_stock - aggregated_quantity) < -9999999999.99` with HTTP 422 (`VALIDATION_ERROR`), allow `unit_cost = 0.00` without exposing `unit_cost`, and require exact equality between `SUM(payments.amount)` and the server-calculated `total_amount` (`422 PAYMENT_TOTAL_MISMATCH`).

#### Scenario: Rejection of payment total mismatch against server-calculated sale total
- **GIVEN** an authenticated tenant with an active product whose server `sale_price` is `"1500.00"` and `stock = "10.00"`
- **WHEN** the user sends `POST /api/v1/sales` for `quantity = "2.00"` with `payments` totaling `"2999.99"` or `"3000.01"` (including stale client price expectations)
- **THEN** the system SHALL reject the request with HTTP 422 Unprocessable Content (`ErrorResponse` with `code = "PAYMENT_TOTAL_MISMATCH"`), persist zero rows, and leave `products.stock = "10.00"`

#### Scenario: Rejection of inactive product for new sale creation
- **GIVEN** an authenticated tenant with a deactivated product (`is_active = false`) in its catalog
- **WHEN** the user sends `POST /api/v1/sales` including that inactive `product_id` for a new `client_id`
- **THEN** the system SHALL reject the request with HTTP 422 Unprocessable Content (`ErrorResponse` with `code = "PRODUCT_INACTIVE"`), create no sale rows, and leave product stock untouched

#### Scenario: Rejection of float values, excessive decimal places, non-positive amounts, and overflow
- **GIVEN** an authenticated tenant session
- **WHEN** the client supplies a raw JSON `float` (e.g. `1.5`), boolean, `NaN`/`Infinity`, >2 decimal places (e.g. `"1.234"`), `quantity <= 0`, `amount <= 0`, values exceeding `"9999999999.99"`, or inputs whose product total rounds to `"0.00"` or overflows `"9999999999.99"`
- **THEN** the system SHALL reject the request with HTTP 422 (`ErrorResponse` with `code = "VALIDATION_ERROR"`) without persisting any sale or mutating stock

#### Scenario: Rejection of aggregated stock deduction or resulting negative stock overflowing numeric(12,2)
- **GIVEN** an authenticated tenant with an active product whose `sale_price = "0.01"` and `stock = "10.00"` OR already negative `stock = "-1.00"`
- **WHEN** the user sends `POST /api/v1/sales` with multiple lines whose aggregated deduction for the same product exceeds `"9999999999.99"` (e.g. `"6000000000.00"` + `"6000000000.00"`) OR a quantity pushing `stock - total_quantity` below `"-9999999999.99"` (e.g. `stock = "-1.00"` with `quantity = "9999999999.00"`), versus a boundary sale where `stock - total_quantity == "-9999999999.99"`
- **THEN** overflowing requests SHALL be rejected cleanly with HTTP 422 (`ErrorResponse` with `code = "VALIDATION_ERROR"`) without causing database numeric overflow (`500` / `22003`) or altering stock, while the `"-9999999999.99"` boundary sale SHALL succeed with HTTP 201 Created

#### Scenario: Rejection of empty items, empty payments, invalid payment method, invalid UUID, or NUL bytes
- **GIVEN** an authenticated tenant session
- **WHEN** the client submits empty `items: []`, empty `payments: []`, an unsupported `payment_method` (e.g. `"other"`, `"CASH"`, `"crypto"`), a malformed UUID for `client_id` or `product_id`, or strings containing `\x00`
- **THEN** Pydantic v2 validation SHALL reject the payload with HTTP 422 (`ErrorResponse` with `code = "VALIDATION_ERROR"`) before executing database writes

#### Scenario: Enforcement of items and payments batch limits and zero unit_cost support
- **GIVEN** an authenticated tenant with an active product having `cost_price = "0.00"` and `sale_price = "10.00"`
- **WHEN** the user submits valid requests at the upper batch bounds (`500` items or `20` payments), oversized batches (`501` items or `21` payments), and a sale referencing the zero-cost product
- **THEN** requests with `500` items, `20` payments, and `cost_price = "0.00"` SHALL succeed with HTTP 201 Created (freezing `unit_cost = 0.00` in persistence while omitting `unit_cost` from `SaleResponse`), and requests with `501` items or `21` payments SHALL fail with HTTP 422 (`ErrorResponse` with `code = "VALIDATION_ERROR"`)

---

### Requirement: OpenAPI Contract Documentation and Uniform Error Schema
The system SHALL register the sales router under `/api/v1` with OpenAPI metadata (`tags=["sales"]`, `SaleCreate`, `SaleResponse`, and error responses `401`, `403`, `404`, `409`, `422` using `ErrorResponse`, plus `200` and `201` responses), SHALL declare `"type": "string"` with decimal format metadata (excluding `"type": "number"`) for `SaleItemCreate.quantity` and `SalePaymentCreate.amount` in OpenAPI JSON Schema consistent with runtime `float` rejection, SHALL synchronize `docs/api/openapi.json`, and SHALL ensure all HTTP and validation error responses from sales endpoints conform strictly to `ErrorResponse` (`{ "code", "message", "details" }`).

#### Scenario: Sales route and schemas documented in OpenAPI schema
- **GIVEN** the running FastAPI application and exported `docs/api/openapi.json`
- **WHEN** requesting `GET /openapi.json` and running `export_openapi --check`
- **THEN** the OpenAPI document SHALL expose `POST /api/v1/sales` with tag `"sales"`, schemas `SaleCreate`, `SaleItemCreate`, `SalePaymentCreate`, `SaleResponse`, `SaleItemResponse`, `SalePaymentResponse`, and `ErrorResponse`, declare `"type": "string"` (without `"number"`) on `SaleItemCreate.quantity` and `SalePaymentCreate.amount`, document status codes `200`, `201`, `401`, `403`, `404`, `409`, and `422`, and match `docs/api/openapi.json` without drift

#### Scenario: All sales error responses conform to uniform ErrorResponse format
- **GIVEN** any error condition (`401`, `403`, `404`, `409`, or `422`) on `POST /api/v1/sales`
- **WHEN** the backend returns the error response
- **THEN** the JSON body SHALL contain exactly the top-level keys `code`, `message`, and `details` without FastAPI's default `detail` wrapper

## ADDED Requirements

### Requirement: Tenant-Scoped Bulk Stock Deduction and Defense-in-Depth Product Queries
The system SHALL enforce explicit `business_id` filtering in addition to PostgreSQL RLS on all catalog product queries invoked during sale registration (product row locking, product name resolution, and stock deduction) and SHALL execute multi-product stock deduction in a single atomic SQL `UPDATE` statement (`CASE WHEN`) rather than N sequential per-product updates.

#### Scenario: Multi-product sale deducts stock in one tenant-filtered UPDATE statement
- **GIVEN** an authenticated tenant with two or more active products in its catalog
- **WHEN** the user registers a valid sale containing multiple distinct products via `POST /api/v1/sales`
- **THEN** the backend SHALL include explicit `business_id` predicates on product lock, name lookup, and stock deduction queries under RLS, execute exactly one bulk `UPDATE products` statement to deduct stock for all sold products, and leave every referenced product's stock accurately updated
