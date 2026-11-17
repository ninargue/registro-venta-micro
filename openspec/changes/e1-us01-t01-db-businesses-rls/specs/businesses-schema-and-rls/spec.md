## ADDED Requirements

### Requirement: Businesses Table Structure and Integrity Constraints
The database SHALL provide a table `businesses` to store tenant organisations with primary key `id UUID`, mandatory `name varchar(100)`, mandatory `country varchar(2)`, mandatory `timezone varchar(50)`, and audit timestamps `created_at` and `updated_at` in `timestamptz`.

#### Scenario: Business record insertion with valid attributes
- **GIVEN** a valid UUID, a non-empty name, a 2-character country code, and a recognized IANA timezone
- **WHEN** an insert statement is executed on `businesses`
- **THEN** the database SHALL store the record successfully with default timestamps populated

#### Scenario: Rejection of null values on mandatory attributes
- **GIVEN** an insert statement omitting `name`, `country`, or `timezone`
- **WHEN** the statement is executed against `businesses`
- **THEN** the database SHALL raise a `NOT NULL` violation error and reject the transaction

#### Scenario: Constraint on country code format
- **GIVEN** an insert statement with a `country` code differing from 2 characters (e.g. "ARG" or "A")
- **WHEN** the insert is executed against `businesses`
- **THEN** the database SHALL violate the check constraint and reject the insert

---

### Requirement: Business Users Association and Role Assignment
The database SHALL provide a junction table `business_users` mapping users to businesses with compound primary key `(business_id, user_id)`, a foreign key to `businesses(id)` with `ON DELETE CASCADE`, a valid `role` restricted to `('owner', 'cashier')`, and a `created_at` timestamp.

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

---

### Requirement: Row-Level Security Isolation via Session Context
The database SHALL enforce row-level security on `businesses` and `business_users`, ensuring that queries only return rows matching `app.current_business_id` set in the current transaction.

#### Scenario: Tenant reads own business data when context matches
- **GIVEN** a database session where `SET LOCAL app.current_business_id = '<business_id>'` is executed
- **WHEN** selecting from `businesses` or `business_users`
- **THEN** the database SHALL return only the rows belonging to `<business_id>`

#### Scenario: Cross-tenant access blocked by RLS policy
- **GIVEN** two distinct businesses A and B, and a session where `SET LOCAL app.current_business_id = 'A'`
- **WHEN** querying `businesses` or `business_users` filtering for business B
- **THEN** the database RLS policy SHALL filter out the records, returning 0 rows

#### Scenario: Access without tenant context returns empty set
- **GIVEN** a session without `app.current_business_id` set (or set to null / empty string)
- **WHEN** selecting from `businesses` or `business_users` under RLS
- **THEN** the database SHALL return 0 rows
