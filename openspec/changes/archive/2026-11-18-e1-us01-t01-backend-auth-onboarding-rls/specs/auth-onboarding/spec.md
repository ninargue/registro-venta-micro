## ADDED Requirements

### Requirement: User Authentication via Login
The system SHALL provide an endpoint `POST /api/v1/auth/login` to authenticate users using their email and password against Supabase Auth, resolve any existing business membership from `business_users` under transaction-local `app.current_user_id` RLS context (and `businesses` under `app.current_business_id`), and issue a signed JWT session token in a secure `HttpOnly; SameSite=Strict` cookie.

#### Scenario: Successful login with existing business
- **GIVEN** a registered user in Supabase Auth who owns or belongs to an active business in `business_users`
- **WHEN** the user submits valid email and password to `POST /api/v1/auth/login`
- **THEN** the system SHALL validate credentials via Supabase Auth, resolve the membership inside a transaction running as `app_api` with `SET LOCAL app.current_user_id = '<user_id>'` followed by `SET LOCAL app.current_business_id = '<business_id>'`, set the `HttpOnly` JWT session cookie containing `user_id`, `business_id`, and `role`, and return HTTP 200 with `requires_onboarding: false` and the `business` summary

#### Scenario: Successful login requiring onboarding
- **GIVEN** a registered user in Supabase Auth who has no row in `business_users`
- **WHEN** the user submits valid credentials to `POST /api/v1/auth/login`
- **THEN** the system SHALL query `business_users` under `SET LOCAL app.current_user_id = '<user_id>'` without deadlock, set the `HttpOnly` JWT session cookie with `user_id` and `business_id: null`, and return HTTP 200 with `requires_onboarding: true` and `business: null`

#### Scenario: Invalid credentials
- **GIVEN** an unregistered user or an invalid password
- **WHEN** credentials are submitted to `POST /api/v1/auth/login`
- **THEN** the system SHALL return HTTP 401 Unauthorized with a generic error payload `{ "code", "message", "details" }` and SHALL NOT set any session cookie

---

### Requirement: Business Onboarding and IANA Timezone Validation
The system SHALL provide an endpoint `POST /api/v1/auth/onboarding` allowing an authenticated user without a business to create a single business as `owner`, validating `country` against `COUNTRY_TIMEZONES` and validating `timezone` (whether explicitly provided or resolved from `COUNTRY_TIMEZONES`) against `zoneinfo.ZoneInfo` in Pydantic v2, executing the insert inside a single atomic transaction with `business_id = uuid4()` generated in Python and both `SET LOCAL app.current_user_id` and `SET LOCAL app.current_business_id` configured beforehand, and rejecting duplicate or concurrent creations via `UNIQUE (user_id)` with HTTP 409 Conflict.

#### Scenario: Successful business onboarding with country timezone resolution
- **GIVEN** an authenticated user session without an associated business
- **WHEN** the user submits a valid `name` and a supported ISO 3166-1 alpha-2 `country` code (e.g. `"AR"`) without an explicit `timezone` to `POST /api/v1/auth/onboarding`
- **THEN** the system SHALL resolve the canonical IANA timezone from `COUNTRY_TIMEZONES` (e.g. `"America/Argentina/Buenos_Aires"`), validate it with `zoneinfo.ZoneInfo`, generate `business_id = uuid4()` in Python, set `SET LOCAL app.current_user_id` and `SET LOCAL app.current_business_id` before executing `INSERT INTO businesses ... RETURNING` and `INSERT INTO business_users` with role `'owner'`, refresh the `HttpOnly` JWT session cookie with the new `business_id` and `role: 'owner'`, and return HTTP 201 Created

#### Scenario: Successful business onboarding with explicit valid IANA timezone
- **GIVEN** an authenticated user session without an associated business
- **WHEN** the user submits a valid `name`, a supported `country` code (e.g. `"AR"`), and an explicit valid IANA `timezone` recognized by `zoneinfo.ZoneInfo` (e.g. `"America/Argentina/Cordoba"`, length `<= 50`)
- **THEN** the system SHALL validate the timezone with `zoneinfo.ZoneInfo`, persist the business with that explicit IANA timezone, associate the user as `'owner'`, refresh the `HttpOnly` JWT session cookie, and return HTTP 201 Created

#### Scenario: Onboarding with invalid or unrecognized IANA timezone
- **GIVEN** an authenticated user session without an associated business
- **WHEN** the user submits a valid `name` and `country` along with an unrecognized or malformed `timezone` (e.g. `"Invalid/Timezone"`, `"Mars/Olympus"`, blank string, or exceeding 50 characters)
- **THEN** Pydantic v2 validation using `zoneinfo.ZoneInfo` SHALL reject the payload and return HTTP 422 Unprocessable Entity without executing database inserts

#### Scenario: Onboarding with unsupported or invalid country code
- **GIVEN** an authenticated user session
- **WHEN** the user submits an invalid or unsupported `country` code (e.g. `"XX"` or `"ARG"`) or blank business `name` to `POST /api/v1/auth/onboarding`
- **THEN** the system SHALL return HTTP 422 Unprocessable Entity with validation details

#### Scenario: Unauthenticated onboarding attempt
- **GIVEN** an unauthenticated client request with missing, malformed, or expired session cookie
- **WHEN** a request is sent to `POST /api/v1/auth/onboarding`
- **THEN** the system SHALL return HTTP 401 Unauthorized

#### Scenario: Duplicate business creation attempt
- **GIVEN** an authenticated user who already belongs to an existing business
- **WHEN** the user submits `POST /api/v1/auth/onboarding`
- **THEN** the system SHALL return HTTP 409 Conflict without creating a duplicate row in `businesses` or `business_users`

#### Scenario: Concurrent onboarding requests enforce single business per user
- **GIVEN** an authenticated user without a business submitting concurrent `POST /api/v1/auth/onboarding` requests
- **WHEN** concurrent transactions race against PostgreSQL `UNIQUE (user_id)` constraint (`uq_business_users_user_id`, SQLSTATE `23505`)
- **THEN** at most one request SHALL succeed with HTTP 201 Created, and any conflicting request SHALL roll back its transaction completely (leaving zero orphan records in `businesses`) and return HTTP 409 Conflict

---

### Requirement: Row-Level Security Context Injection
The system SHALL enforce database-level isolation by executing transactional sessions under the non-bypass runtime role `app_api` (via direct connection or `SET LOCAL ROLE app_api`) and injecting transaction-local PostgreSQL context settings (`SET LOCAL app.current_user_id` for pre-tenant user lookups and both `SET LOCAL app.current_user_id` and `SET LOCAL app.current_business_id` for tenant-scoped operations).

#### Scenario: Login membership lookup uses app current user id without deadlock
- **GIVEN** a database transaction executing under role `app_api` with `SET LOCAL app.current_user_id = '<user_id>'` and without `app.current_business_id` set
- **WHEN** querying `business_users` for that user's membership
- **THEN** PostgreSQL RLS policy `business_users_select_isolation` SHALL allow reading only the membership belonging to `<user_id>` without deadlock and filter out memberships of other users

#### Scenario: Valid tenant context set on transactional session
- **GIVEN** an authenticated request whose JWT carries valid `user_id` (`sub`) and `business_id`
- **WHEN** a tenant-scoped endpoint acquires the transactional database dependency
- **THEN** the system SHALL enforce runtime role `app_api` and execute `SET LOCAL app.current_user_id = '<user_id>'` and `SET LOCAL app.current_business_id = '<business_id>'` prior to executing queries, restricting all reads and writes via PostgreSQL RLS

#### Scenario: Request lacking business context blocked from tenant resources
- **GIVEN** a request without a valid JWT session cookie OR an authenticated user whose JWT lacks an active `business_id` (onboarding pending)
- **WHEN** attempting to access a tenant-protected endpoint or dependency
- **THEN** unauthenticated requests SHALL receive HTTP 401 Unauthorized, and authenticated requests without an active `business_id` SHALL receive HTTP 403 Forbidden without executing tenant queries

#### Scenario: Cross-tenant database isolation enforced under app_api
- **GIVEN** two distinct businesses A and B and a transactional session running as `app_api` with `SET LOCAL app.current_business_id = '<business_a>'`
- **WHEN** querying or mutating `businesses` or `business_users` targeting `<business_b>`
- **THEN** PostgreSQL RLS policies SHALL isolate `<business_b>` returning 0 rows and preventing cross-tenant access
