# products-schema-and-rls Specification

## Purpose
TBD - created by archiving change issue-42-esquema-productos-db. Update Purpose after archive.
## Requirements
### Requirement: Products Table Structure, Precision Types, and Foreign Key Integrity
The database SHALL provide a table `public.products` storing per-business catalog items with primary key `id` (`uuid`, default `gen_random_uuid()`), mandatory tenant foreign key `business_id` (`uuid`, referencing `businesses(id)` with `ON DELETE CASCADE`), composite unique key `(business_id, id)` (`uq_products_business_id_id`), optional `code` (`varchar(50)`), mandatory `name` (`varchar(150)`), `sale_price` (`numeric(12,2)` NOT NULL), `cost_price` (`numeric(12,2)` NOT NULL DEFAULT 0), `stock` (`numeric(12,2)` NOT NULL DEFAULT 0), `is_active` (`boolean` NOT NULL DEFAULT true), and audit timestamps `created_at` and `updated_at` (`timestamptz` NOT NULL DEFAULT `now()`). Monetary and stock columns (`sale_price`, `cost_price`, `stock`) SHALL strictly use `numeric(12,2)` and MUST NEVER use `float`, `real`, or `double precision`.

#### Scenario: Product insertion with valid attributes and defaults
- **GIVEN** an existing business in `businesses`
- **WHEN** inserting a product specifying `business_id`, `name`, and `sale_price` (with optional `code`, `cost_price`, `stock`, and `is_active` omitted or provided)
- **THEN** the database SHALL store the row with a generated `id` UUID, `cost_price = 0.00`, `stock = 0.00`, `is_active = true`, populated `created_at`/`updated_at` timestamps, and exact `numeric(12,2)` decimal representation

#### Scenario: Exact decimal precision without floating-point drift
- **GIVEN** an existing business and a product with `sale_price = 19.99`, `cost_price = 0.10`, and `stock = 0.20`
- **WHEN** querying `information_schema.columns` for `products` and executing decimal arithmetic (`cost_price + stock`)
- **THEN** `sale_price`, `cost_price`, and `stock` SHALL report `data_type = 'numeric'`, `numeric_precision = 12`, `numeric_scale = 2`, and arithmetic SHALL evaluate exactly to `0.30`

#### Scenario: Rejection of null values on mandatory attributes
- **GIVEN** an existing business
- **WHEN** attempting to insert into `products` omitting or passing `NULL` for `business_id`, `name`, or `sale_price`
- **THEN** the database SHALL raise a `NOT NULL` violation (`23502`) and reject the insert

#### Scenario: Rejection of orphan business reference
- **GIVEN** a `business_id` UUID that does not exist in `businesses`
- **WHEN** attempting to insert a product with that `business_id`
- **THEN** the database SHALL raise a foreign key violation (`23503`) and reject the insert

#### Scenario: Cascade deletion when parent business is removed
- **GIVEN** an existing business with associated rows in `products`
- **WHEN** deleting the parent record in `businesses`
- **THEN** all associated `products` rows for that business SHALL be deleted automatically via `ON DELETE CASCADE`

---

### Requirement: Product Domain Check Constraints and Counter Stock Semantics
The database SHALL enforce check constraints on `products` requiring `char_length(trim(name)) > 0`, `code IS NULL OR char_length(trim(code)) > 0`, `sale_price > 0`, and `cost_price >= 0`. The `stock` column (`numeric(12,2)`) SHALL default to `0.00` without a `CHECK (stock >= 0)` database constraint so atomic counter-sale deductions (`stock = stock - quantity`) can persist transient negative stock balances per US-03 while initial non-negative stock on creation is enforced by the API layer.

#### Scenario: Rejection of blank product name or blank non-null code
- **GIVEN** an existing business
- **WHEN** attempting to insert or update a product with whitespace-only `name` (`'   '`) or non-null whitespace-only `code` (`''` or `'  '`)
- **THEN** the database SHALL reject the statement with a check constraint violation (`23514`)

#### Scenario: Rejection of zero or negative sale_price
- **GIVEN** an existing business
- **WHEN** attempting to insert or update a product with `sale_price = 0.00` or `sale_price = -5.00`
- **THEN** the database SHALL reject the statement with a check constraint violation (`23514`)

#### Scenario: Rejection of negative cost_price while allowing zero cost
- **GIVEN** an existing business
- **WHEN** inserting a product with `cost_price = 0.00` and another attempt with `cost_price = -0.01`
- **THEN** `cost_price = 0.00` SHALL succeed and `cost_price = -0.01` SHALL be rejected with a check constraint violation (`23514`)

#### Scenario: Atomic stock deduction supports transient negative balance
- **GIVEN** a product with `stock = 2.00`
- **WHEN** executing an atomic deduction `UPDATE products SET stock = stock - 3.00`
- **THEN** the database SHALL persist `stock = -1.00` in exact `numeric(12,2)` without raising a constraint error

---

### Requirement: Partial Uniqueness of Product Code per Business
The database SHALL enforce uniqueness on `(business_id, code)` only where `code IS NOT NULL` (`uq_products_business_id_code`), permitting multiple products without `code` (`NULL`) inside the same business and permitting identical `code` values across distinct businesses.

#### Scenario: Multiple products without code allowed in the same business
- **GIVEN** an existing business
- **WHEN** inserting two distinct products in the same business both with `code = NULL`
- **THEN** the database SHALL persist both products without uniqueness conflict

#### Scenario: Duplicate non-null code within the same business rejected
- **GIVEN** an existing product in business A with `code = 'SKU-001'`
- **WHEN** attempting to insert or update another product in business A with `code = 'SKU-001'`
- **THEN** the database SHALL reject the statement with a unique constraint violation (`23505`)

#### Scenario: Same non-null code allowed across distinct businesses
- **GIVEN** an existing product in business A with `code = 'SKU-001'`
- **WHEN** inserting a product in business B with `code = 'SKU-001'`
- **THEN** the database SHALL persist the product in business B successfully

---

### Requirement: Soft Deactivation and Automatic updated_at Trigger
The `products` table SHALL support logical deactivation via `is_active` (default `true`) to preserve referential integrity with future sales records, and SHALL attach a `BEFORE UPDATE` trigger (`trg_products_set_updated_at`) invoking `public.set_products_updated_at()` using `clock_timestamp()` so `updated_at` automatically advances on every row modification.

#### Scenario: Product deactivation preserves record and advances updated_at
- **GIVEN** an active product (`is_active = true`) with recorded `created_at` and `updated_at`
- **WHEN** updating the product to `is_active = false` or modifying its `sale_price` or `stock` within a transaction
- **THEN** the row SHALL remain persisted with `is_active = false` and `updated_at` SHALL be strictly greater than its prior `updated_at` value

---

### Requirement: Forced Row-Level Security Isolation Across All DML Operations
The database SHALL enable and force Row-Level Security (`ENABLE ROW LEVEL SECURITY` and `FORCE ROW LEVEL SECURITY`) on `products` with granular policies per operation (`SELECT`, `INSERT`, `UPDATE` with `USING` and `WITH CHECK`, and `DELETE`) evaluating `business_id = NULLIF(current_setting('app.current_business_id', true), '')::uuid`.

#### Scenario: Authorized tenant executes SELECT, INSERT, UPDATE, and DELETE on own products
- **GIVEN** a database session running as `app_api` (or `app_runtime`) with `SET LOCAL app.current_business_id = '<business_a>'`
- **WHEN** inserting, selecting, updating, and deleting a product belonging to `<business_a>`
- **THEN** the database SHALL execute all operations successfully and return only rows of `<business_a>`

#### Scenario: Cross-tenant SELECT, UPDATE, and DELETE blocked by RLS
- **GIVEN** products belonging to business A and business B, and a session running as `app_api` (or `app_runtime`) with `SET LOCAL app.current_business_id = '<business_a>'`
- **WHEN** selecting, updating, or deleting rows belonging to business B (filtered or unfiltered)
- **THEN** the database SHALL return 0 rows on `SELECT` and affect 0 rows on `UPDATE` and `DELETE` for business B, leaving business B's rows intact

#### Scenario: Cross-tenant INSERT and UPDATE business_id hijacking rejected by WITH CHECK
- **GIVEN** a session running as `app_api` (or `app_runtime`) with `SET LOCAL app.current_business_id = '<business_a>'` and an existing product in business A
- **WHEN** attempting to insert a product with `business_id = '<business_b>'` OR attempting to update an existing product setting `business_id = '<business_b>'`
- **THEN** the database SHALL reject both operations with an RLS policy violation (`42501`)

#### Scenario: Access without tenant context returns empty set and blocks writes
- **GIVEN** a session running as `app_api` (or `app_runtime`) with `app.current_business_id` unset or set to empty string `''`
- **WHEN** executing `SELECT`, `UPDATE`, `DELETE`, or `INSERT` on `products`
- **THEN** `SELECT` SHALL return 0 rows, `UPDATE`/`DELETE` SHALL affect 0 rows, and `INSERT` SHALL fail with SQLSTATE `42501`

---

### Requirement: Runtime Role Privileges and DCL Non-Bypass Guarantees
The database SHALL revoke all privileges (`REVOKE ALL`) on `products` from `PUBLIC`, `anon`, and `authenticated`, and SHALL grant explicit DML privileges (`SELECT`, `INSERT`, `UPDATE`, `DELETE`) on `products` exclusively to `app_api` (inherited by `app_runtime`), without `TRUNCATE` privileges and without table ownership or `BYPASSRLS`.

#### Scenario: Table metadata confirms forced RLS and non-privileged ownership boundary
- **GIVEN** a migrated database
- **WHEN** inspecting `pg_class`, `pg_tables`, and `pg_roles` for `products`, `app_api`, and `app_runtime`
- **THEN** `products` SHALL have `relrowsecurity = true` and `relforcerowsecurity = true`, its owner SHALL NOT be `app_api` or `app_runtime`, and both roles SHALL have `rolsuper = false` and `rolbypassrls = false`

#### Scenario: Role app_runtime enforces RLS and cannot truncate products
- **GIVEN** products for business A and business B and a session running directly under `SET LOCAL ROLE app_runtime` with `SET LOCAL app.current_business_id = '<business_a>'`
- **WHEN** querying products of business B or executing `TRUNCATE products`
- **THEN** querying business B SHALL return 0 rows and `TRUNCATE products` SHALL be rejected with SQLSTATE `42501`

#### Scenario: Roles authenticated and anon cannot access or truncate products
- **GIVEN** a migrated database with rows in `products`
- **WHEN** a session running as `authenticated` or `anon` attempts `SELECT`, `INSERT`, `UPDATE`, `DELETE`, or `TRUNCATE` on `products`
- **THEN** the database SHALL reject every operation with SQLSTATE `42501`

