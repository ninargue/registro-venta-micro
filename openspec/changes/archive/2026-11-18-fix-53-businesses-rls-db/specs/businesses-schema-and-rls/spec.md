## MODIFIED Requirements

### Requirement: Business Users Association and Role Assignment
The database SHALL provide a junction table `business_users` mapping users to businesses with compound primary key `(business_id, user_id)`, a uniqueness constraint `UNIQUE (user_id)` enforcing the MVP single-business-per-owner invariant and onboarding idempotency, a foreign key to `businesses(id)` with `ON DELETE CASCADE`, a valid `role` restricted to `('owner', 'cashier')`, and a `created_at` timestamp.

#### Scenario: Successful association of user to business
- **GIVEN** an existing `business_id` and a user UUID with role `'owner'`
- **WHEN** inserting into `business_users`
- **THEN** the database SHALL persist the membership successfully

#### Scenario: Rejection of invalid user roles
- **GIVEN** a membership insert specifying an unrecognized role such as `'superadmin'` or `'guest'`
- **WHEN** inserting into `business_users`
- **THEN** the database SHALL reject the row via a `CHECK (role IN ('owner', 'cashier'))` constraint

#### Scenario: Cascade deletion on business removal
- **GIVEN** an existing business with associated rows in `business_users`
- **WHEN** the parent record in `businesses` is deleted
- **THEN** all associated records in `business_users` SHALL be deleted automatically via foreign key cascade

#### Scenario: Rejection of duplicate business membership for the same user
- **GIVEN** an existing membership row in `business_users` associating a user with business A
- **WHEN** an insert statement attempts to associate the same `user_id` with business B (or repeat onboarding for the same user)
- **THEN** the database SHALL raise a unique constraint violation (`23505`) and reject the insert

---

### Requirement: Row-Level Security Isolation via Session Context
The database SHALL enforce forced row-level security (`ENABLE` and `FORCE ROW LEVEL SECURITY`) on `businesses` and `business_users` using transaction-local session variables `app.current_business_id` and `app.current_user_id`. On `businesses`, queries and mutations SHALL match `app.current_business_id` (with controlled onboarding insert). On `business_users`, `SELECT` SHALL permit rows matching `app.current_business_id` OR `user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid` to resolve login lookups without deadlock; `INSERT` SHALL require `user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid` (and consistency with `app.current_business_id` when set); and `UPDATE`/`DELETE` SHALL require `business_id = NULLIF(current_setting('app.current_business_id', true), '')::uuid` (including `WITH CHECK` on `UPDATE`).

#### Scenario: Tenant reads own business data when context matches
- **GIVEN** a database session where `SET LOCAL app.current_business_id = '<business_id>'` is executed
- **WHEN** selecting from `businesses` or `business_users`
- **THEN** the database SHALL return only the rows belonging to `<business_id>`

#### Scenario: Cross-tenant access blocked by RLS policy
- **GIVEN** two distinct businesses A and B, and a session where `SET LOCAL app.current_business_id = 'A'`
- **WHEN** querying `businesses` or `business_users` filtering for business B
- **THEN** the database RLS policy SHALL filter out the records, returning 0 rows

#### Scenario: Access without tenant or user context returns empty set
- **GIVEN** a session without `app.current_business_id` or `app.current_user_id` set (or both set to null / empty string)
- **WHEN** selecting from `businesses` or `business_users` under RLS
- **THEN** the database SHALL return 0 rows

#### Scenario: User resolves own membership during login using app.current_user_id
- **GIVEN** a database session running under the runtime role `app_api` with `SET LOCAL app.current_user_id = '<user_a>'` and without `app.current_business_id` set
- **WHEN** selecting from `business_users`
- **THEN** the database SHALL return only the membership row belonging to `<user_a>` and filter out rows of other users

#### Scenario: Cross-user membership read blocked when only app.current_user_id is set
- **GIVEN** two distinct users A and B belonging to businesses 1 and 2, and a session running as `app_api` with `SET LOCAL app.current_user_id = '<user_a>'`
- **WHEN** querying `business_users` filtering for `<user_b>`
- **THEN** the database RLS policy SHALL filter out user B's record and return 0 rows

#### Scenario: Authenticated user inserts own membership during onboarding
- **GIVEN** a database session running as `app_api` with `SET LOCAL app.current_user_id = '<user_a>'` and an existing business
- **WHEN** inserting a membership row with `user_id = '<user_a>'` and role `'owner'` into `business_users`
- **THEN** the database SHALL allow the insert via the `WITH CHECK` policy

#### Scenario: Impersonated insert for another user_id rejected by RLS
- **GIVEN** a database session running as `app_api` with `SET LOCAL app.current_user_id = '<user_a>'` (with or without `app.current_business_id` set)
- **WHEN** attempting to insert a membership row for a different `user_id = '<user_b>'` into `business_users`
- **THEN** the database SHALL reject the insert with an RLS policy violation (`42501`)

#### Scenario: Unauthenticated insert without user context rejected by RLS
- **GIVEN** a database session running as `app_api` without `app.current_user_id` set (or set to empty string)
- **WHEN** attempting to insert any row into `business_users`
- **THEN** the database SHALL reject the insert with an RLS policy violation (`42501`)

#### Scenario: Cross-tenant insert when active business_id mismatches rejected by RLS
- **GIVEN** a database session running as `app_api` with `SET LOCAL app.current_user_id = '<user_a>'` and `SET LOCAL app.current_business_id = '<business_1>'`
- **WHEN** attempting to insert a membership row with `business_id = '<business_2>'` into `business_users`
- **THEN** the database SHALL reject the insert with an RLS policy violation (`42501`)

#### Scenario: Cross-tenant update hijack on business_users rejected by RLS
- **GIVEN** a database session running as `app_api` with `SET LOCAL app.current_business_id = '<business_1>'` and an existing membership row in business 1
- **WHEN** attempting to update `business_id` of that row to `<business_2>`
- **THEN** the database SHALL reject the update via `WITH CHECK` with an RLS policy violation (`42501`)

---

## ADDED Requirements

### Requirement: Runtime Role Privileges and RLS Non-Bypass Guarantees
The database SHALL ensure the runtime role `app_api` exists as a non-superuser, non-table-owner role without `BYPASSRLS` (`NOSUPERUSER`, `NOBYPASSRLS`, `NOCREATEROLE`, `NOCREATEDB`) and SHALL grant explicit DML privileges (`SELECT`, `INSERT`, `UPDATE`, `DELETE`) on `businesses` and `business_users` (plus `USAGE` on schema `public`) to `app_api` so all backend operations execute strictly under enforced RLS without `TRUNCATE` privileges.

#### Scenario: Runtime role app_api has no RLS bypass or table ownership privileges
- **GIVEN** a migrated database
- **WHEN** inspecting `pg_roles` for `app_api` and `pg_tables` for ownership of `businesses` and `business_users`
- **THEN** `app_api` SHALL exist with `rolsuper = false` and `rolbypassrls = false`, and SHALL NOT be the owner of `businesses` or `business_users`

#### Scenario: Runtime role app_api performs permitted operations under RLS context
- **GIVEN** a database session running as `app_api` with valid `app.current_user_id` and `app.current_business_id` context
- **WHEN** executing `SELECT`, `INSERT`, and `UPDATE` on `businesses` and `business_users` within its authorized scope
- **THEN** the database SHALL execute all operations successfully

#### Scenario: Runtime role app_api cannot bypass RLS on cross-tenant rows or truncate tables
- **GIVEN** two distinct businesses 1 and 2 and a session running as `app_api` with `SET LOCAL app.current_business_id = '<business_1>'`
- **WHEN** attempting to read, update, or delete rows belonging to business 2, or truncate `businesses` / `business_users`
- **THEN** the database SHALL return/affect 0 rows for business 2 and deny `TRUNCATE` with a privilege error (`42501`)
