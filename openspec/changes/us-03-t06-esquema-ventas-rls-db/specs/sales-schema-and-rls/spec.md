## ADDED Requirements

### Requirement: Sales Table Structure, Precision Types, and Idempotency Uniqueness
The database SHALL provide a table `public.sales` storing per-business sale headers with primary key `id` (`uuid`, `pk_sales`, default `gen_random_uuid()`), mandatory tenant foreign key `business_id` (`uuid`, referencing `businesses(id)` with `ON DELETE CASCADE`, `fk_sales_business_id`), composite unique key `(business_id, id)` (`uq_sales_business_id_id`), mandatory idempotency identifier `client_id` (`uuid`, NOT NULL) with composite uniqueness `(business_id, client_id)` (`uq_sales_business_id_client_id`), `total_amount` (`numeric(12,2)` NOT NULL, `CHECK (total_amount > 0)`), audit timestamp `created_at` (`timestamptz` NOT NULL DEFAULT `now()`), and composite index `(business_id, created_at)` (`ix_sales_business_id_created_at`). Monetary columns SHALL strictly use `numeric(12,2)` and MUST NEVER use `float`, `real`, or `double precision`.

#### Scenario: Sale insertion with valid attributes and defaults
- **GIVEN** an existing business in `businesses` and a client-generated UUID `client_id`
- **WHEN** inserting a row into `sales` specifying `business_id`, `client_id`, and `total_amount > 0`
- **THEN** the database SHALL persist the row with a generated `id` UUID, exact `numeric(12,2)` representation for `total_amount`, and a populated UTC `created_at` timestamp

#### Scenario: Rejection of null values on mandatory sales attributes
- **GIVEN** an existing business
- **WHEN** attempting to insert into `sales` passing `NULL` or omitting `business_id`, `client_id`, `total_amount`, or explicitly passing `NULL` for `created_at`
- **THEN** the database SHALL raise a `NOT NULL` violation (`23502`) and reject the statement

#### Scenario: Rejection of zero or negative total_amount
- **GIVEN** an existing business
- **WHEN** attempting to insert or update a row in `sales` with `total_amount = 0.00` or `total_amount = -10.00`
- **THEN** the database SHALL reject the statement with a check constraint violation (`23514`)

#### Scenario: Duplicate client_id within same business does not duplicate records and supports idempotency
- **GIVEN** an existing sale in business A with a given `client_id`
- **WHEN** attempting a direct second `INSERT` with the same `(business_id, client_id)` AND when executing `INSERT ... ON CONFLICT (business_id, client_id) DO NOTHING`
- **THEN** the direct duplicate `INSERT` SHALL be rejected with a unique constraint violation (`23505`), the `ON CONFLICT DO NOTHING` statement SHALL return 0 inserted rows without error, and `sales` SHALL retain exactly 1 row for that `(business_id, client_id)`

#### Scenario: Same client_id allowed across distinct businesses without cross-tenant collision
- **GIVEN** an existing sale in business A with a specific `client_id` UUID
- **WHEN** inserting a sale in business B with the identical `client_id` UUID
- **THEN** the database SHALL persist the sale in business B without uniqueness conflict

#### Scenario: Rejection of orphan business_id and cascade deletion from business
- **GIVEN** a non-existent `business_id` UUID for an orphan insert test, and an existing business with sales (without blocking restricted items) for cascade deletion
- **WHEN** attempting to insert a sale with the non-existent `business_id`, or deleting the existing parent business
- **THEN** the orphan insert SHALL fail with a foreign key violation (`23503`) and deleting the parent business SHALL automatically delete its associated `sales` rows via `ON DELETE CASCADE`

---

### Requirement: Sale Items Table Structure, Frozen Snapshots, and Composite Referential Integrity
The database SHALL provide a table `public.sale_items` storing line items per sale with primary key `id` (`uuid`, `pk_sale_items`, default `gen_random_uuid()`), `business_id` (`uuid` NOT NULL, `FK -> businesses(id) ON DELETE CASCADE`), `sale_id` (`uuid` NOT NULL), `product_id` (`uuid` NOT NULL), `quantity` (`numeric(12,2)` NOT NULL, `CHECK (quantity > 0)`), frozen `unit_price` (`numeric(12,2)` NOT NULL, `CHECK (unit_price > 0)`), frozen `unit_cost` (`numeric(12,2)` NOT NULL, `CHECK (unit_cost >= 0)`), and `created_at` (`timestamptz` NOT NULL DEFAULT `now()`). Referential integrity SHALL be enforced via composite foreign keys `(business_id, sale_id) REFERENCES sales(business_id, id) ON DELETE CASCADE` (`fk_sale_items_sale`) and `(business_id, product_id) REFERENCES products(business_id, id) ON DELETE RESTRICT` (`fk_sale_items_product`), supported by indexes `(business_id, sale_id)` and `(business_id, product_id)`.

#### Scenario: Sale item insertion freezes unit_price and unit_cost independently of later product edits
- **GIVEN** an existing business, a product with `sale_price = 1500.00` and `cost_price = 900.00`, and an existing sale for that business
- **WHEN** inserting a `sale_items` row freezing `unit_price = 1500.00` and `unit_cost = 900.00`, and subsequently updating `products.sale_price` to `2000.00` and `products.cost_price` to `1100.00`
- **THEN** the stored `sale_items` row SHALL retain `unit_price = 1500.00` and `unit_cost = 900.00` unchanged

#### Scenario: Exact decimal precision across sales, sale_items, and payments without floating-point drift
- **GIVEN** migrated tables `sales`, `sale_items`, and `payments`
- **WHEN** querying `information_schema.columns` for `total_amount`, `quantity`, `unit_price`, `unit_cost`, and `amount` and evaluating decimal arithmetic (`0.10 + 0.20` and `quantity * unit_cost`)
- **THEN** all five columns SHALL report `data_type = 'numeric'`, `numeric_precision = 12`, and `numeric_scale = 2`, and decimal addition `0.10 + 0.20` SHALL evaluate exactly to `0.30`

#### Scenario: Rejection of null values and invalid numeric bounds on sale_items
- **GIVEN** an existing sale and product in the same business
- **WHEN** attempting to insert `NULL` in `business_id`, `sale_id`, `product_id`, `quantity`, `unit_price`, `unit_cost`, or `created_at`, OR inserting/updating `quantity <= 0`, `unit_price <= 0`, or `unit_cost < 0` (while testing `unit_cost = 0.00`)
- **THEN** `unit_cost = 0.00` SHALL succeed, `NULL` values SHALL fail with `23502`, and out-of-range numeric values SHALL fail with `23514`

#### Scenario: Cross-business sale_id or product_id reference rejected by composite foreign keys
- **GIVEN** business A with sale S1 and product P1, and business B with sale S2 and product P2
- **WHEN** attempting to insert a `sale_items` row with `(business_id = B, sale_id = S1, product_id = P2)` OR `(business_id = B, sale_id = S2, product_id = P1)`
- **THEN** the database SHALL reject both cross-tenant associations with a foreign key violation (`23503`)

#### Scenario: Physical deletion of referenced product is restricted while deleting a sale cascades to its items
- **GIVEN** an existing sale with associated `sale_items` referencing a product
- **WHEN** attempting `DELETE FROM products` for the referenced product, and subsequently executing `DELETE FROM sales` for the parent sale
- **THEN** `DELETE FROM products` SHALL be rejected with a foreign key violation (`23503`) preserving historical integrity, and `DELETE FROM sales` SHALL delete the associated `sale_items` rows via `ON DELETE CASCADE`

---

### Requirement: Payments Table Structure, Allowed Methods, and Referential Integrity
The database SHALL provide a table `public.payments` storing payment breakdowns per sale with primary key `id` (`uuid`, `pk_payments`, default `gen_random_uuid()`), `business_id` (`uuid` NOT NULL, `FK -> businesses(id) ON DELETE CASCADE`), `sale_id` (`uuid` NOT NULL), `payment_method` (`varchar(20)` NOT NULL, `CHECK (payment_method IN ('cash', 'card', 'transfer'))`), `amount` (`numeric(12,2)` NOT NULL, `CHECK (amount > 0)`), and `created_at` (`timestamptz` NOT NULL DEFAULT `now()`). Referential integrity SHALL be enforced via composite foreign key `(business_id, sale_id) REFERENCES sales(business_id, id) ON DELETE CASCADE` (`fk_payments_sale`) and indexed via `(business_id, sale_id)` (`ix_payments_business_id_sale_id`).

#### Scenario: Multiple combined payment rows persisted for a single sale across valid methods
- **GIVEN** an existing business and sale
- **WHEN** inserting multiple rows into `payments` for that `sale_id` with `payment_method` values `'cash'`, `'card'`, and `'transfer'` and positive `amount` values
- **THEN** the database SHALL persist all payment rows in `numeric(12,2)` linked to the sale

#### Scenario: Rejection of invalid payment_method, non-positive amount, and mandatory nulls
- **GIVEN** an existing business and sale
- **WHEN** attempting to insert or update a row in `payments` with an unrecognized `payment_method` (such as `'other'`, `'crypto'`, or `''`), with `amount <= 0` (`0.00` or `-1.00`), or with `NULL` in `business_id`, `sale_id`, `payment_method`, `amount`, or `created_at`
- **THEN** unrecognized methods and non-positive amounts SHALL fail with `23514`, and `NULL` values SHALL fail with `23502`

#### Scenario: Cross-business sale_id reference rejected and cascade deletion from sale removes payments
- **GIVEN** business A with sale S1 and business B
- **WHEN** attempting to insert a payment with `(business_id = B, sale_id = S1)`, and when deleting a parent sale in business A that has payments
- **THEN** the cross-business payment insert SHALL fail with a foreign key violation (`23503`), and deleting the parent sale SHALL automatically delete its associated `payments` rows via `ON DELETE CASCADE`

---

### Requirement: Forced Row-Level Security Isolation Across Sales, Sale Items, and Payments
The database SHALL enable and force Row-Level Security (`ENABLE ROW LEVEL SECURITY` and `FORCE ROW LEVEL SECURITY`) on `sales`, `sale_items`, and `payments` with granular policies per operation (`SELECT`, `INSERT`, `UPDATE` with `USING` and `WITH CHECK`, and `DELETE`) evaluating `business_id = NULLIF(current_setting('app.current_business_id', true), '')::uuid`.

#### Scenario: Authorized tenant performs DML and idempotent conflict-safe inserts under app_runtime
- **GIVEN** a database session running as `app_runtime` with `SET LOCAL app.current_business_id = '<business_a>'` and an existing product belonging to `<business_a>`
- **WHEN** inserting into `sales` (including an idempotent retry using `ON CONFLICT (business_id, client_id) DO NOTHING`), inserting into `sale_items` and `payments`, and executing `SELECT`, `UPDATE`, and `DELETE` on rows of `<business_a>`
- **THEN** all authorized operations SHALL succeed, return only `<business_a>` rows, and preserve a single sale row on idempotent retry

#### Scenario: Cross-tenant SELECT, UPDATE, and DELETE blocked by RLS across all three tables
- **GIVEN** sales, sale items, and payments belonging to business A and business B, and a session running as `app_runtime` with `SET LOCAL app.current_business_id = '<business_a>'`
- **WHEN** selecting, updating, or deleting rows belonging to business B (with or without `WHERE` clauses) across `sales`, `sale_items`, and `payments`
- **THEN** `SELECT` SHALL return 0 rows and `UPDATE`/`DELETE` SHALL affect 0 rows for business B, leaving business B data intact

#### Scenario: Cross-tenant INSERT and UPDATE business_id hijacking rejected by WITH CHECK
- **GIVEN** a session running as `app_runtime` with `SET LOCAL app.current_business_id = '<business_a>'` and existing rows in business A
- **WHEN** attempting to insert rows with `business_id = '<business_b>'` (including with `ON CONFLICT DO NOTHING`) OR attempting to update `business_id` to `<business_b>` on `sales`, `sale_items`, or `payments`
- **THEN** the database SHALL reject every cross-tenant write with an RLS policy violation (`42501`)

#### Scenario: Access without tenant context returns empty set and blocks writes
- **GIVEN** a session running as `app_runtime` with `app.current_business_id` unset or set to empty string `''`
- **WHEN** executing `SELECT`, `UPDATE`, `DELETE`, or `INSERT` on `sales`, `sale_items`, and `payments`
- **THEN** `SELECT` SHALL return 0 rows, `UPDATE`/`DELETE` SHALL affect 0 rows, and `INSERT` SHALL fail with SQLSTATE `42501`

---

### Requirement: Runtime Role Privileges and DCL Non-Bypass Guarantees
The database SHALL revoke all privileges (`REVOKE ALL`) on `sales`, `sale_items`, and `payments` from `PUBLIC`, `anon`, and `authenticated`, and SHALL grant explicit DML privileges (`SELECT`, `INSERT`, `UPDATE`, `DELETE`) on all three tables exclusively to `app_api` (inherited by `app_runtime`), without `TRUNCATE` privileges and without table ownership or `BYPASSRLS`.

#### Scenario: Table metadata confirms forced RLS, non-privileged ownership, and exact grants
- **GIVEN** a migrated database
- **WHEN** inspecting `pg_class`, `pg_tables`, `pg_roles`, and `information_schema.role_table_grants` for `sales`, `sale_items`, `payments`, `app_api`, and `app_runtime`
- **THEN** all three tables SHALL have `relrowsecurity = true` and `relforcerowsecurity = true`, their owner SHALL NOT be `app_api` or `app_runtime`, both roles SHALL have `rolsuper = false` and `rolbypassrls = false`, `app_api` SHALL hold exclusively `{SELECT, INSERT, UPDATE, DELETE}`, and `PUBLIC`, `anon`, and `authenticated` SHALL hold zero privileges

#### Scenario: Role app_runtime enforces RLS and cannot truncate sales, sale_items, or payments
- **GIVEN** a session running under `SET LOCAL ROLE app_runtime` with `SET LOCAL app.current_business_id = '<business_a>'`
- **WHEN** attempting `TRUNCATE sales`, `TRUNCATE sale_items`, or `TRUNCATE payments`
- **THEN** PostgreSQL SHALL reject every `TRUNCATE` statement with SQLSTATE `42501`

#### Scenario: Roles authenticated and anon cannot access or truncate sales, sale_items, or payments
- **GIVEN** a migrated database with existing rows in `sales`, `sale_items`, and `payments`
- **WHEN** a session running as `authenticated` or `anon` attempts `SELECT`, `INSERT`, `UPDATE`, `DELETE`, or `TRUNCATE` on any of the three tables
- **THEN** PostgreSQL SHALL reject every statement with SQLSTATE `42501`
