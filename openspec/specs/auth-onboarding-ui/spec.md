# auth-onboarding-ui Specification

## Purpose
TBD - created by archiving change issue-40-login-onboarding-frontend. Update Purpose after archive.
## Requirements
### Requirement: Accessible Login Screen and Client Validation
The application SHALL provide a login route `/login` titled `"Iniciar Sesión — registro-venta-micro"` matching the states (`loading`, `empty`, `error`, `ready`) and accessible elements defined in `docs/ui/auth-onboarding-ui-spec.json`. All interactive controls MUST satisfy ergonomic touch targets (`>= 48px` minimum height/width), proper `<label>` associations, and keyboard submission without depending on external UI libraries.

#### Scenario: Initial login screen renders required semantic elements in empty/ready state
- **GIVEN** an unauthenticated user navigates to `/login`
- **WHEN** the login view finishes rendering in its initial state
- **THEN** the view SHALL expose a region labeled `"Tarjeta de inicio de sesión"`, a level-1 heading `"registro-venta-micro"`, helper text `"Ingresa las credenciales de tu negocio para comenzar a operar."`, a required email input labeled `"Correo electrónico"` with placeholder `"dueño@negocio.com"`, a required password input labeled `"Contraseña"`, a submit button labeled `"Iniciar Sesión"`, and a theme toggle button labeled `"Alternar modo claro / modo oscuro"`

#### Scenario: Client-side validation rejects empty or malformed credentials before network call
- **GIVEN** the user is on `/login`
- **WHEN** the user submits the form with an empty email, an invalid email format, or an empty password
- **THEN** the application SHALL NOT invoke `POST /api/v1/auth/login`, SHALL mark the invalid field(s) with `aria-invalid="true"`, and SHALL announce an accessible validation message inside a `role="alert"` container

#### Scenario: Loading state prevents duplicate submissions while login request is pending
- **GIVEN** the user enters valid credentials on `/login`
- **WHEN** the user submits the form and `POST /api/v1/auth/login` is still in flight
- **THEN** the submit button SHALL be disabled (and reflect busy state) so duplicate requests are not dispatched until the request settles

#### Scenario: Theme toggle switches light and dark mode accessibly
- **GIVEN** the user is on `/login`
- **WHEN** the user activates the button `"Alternar modo claro / modo oscuro"`
- **THEN** the application SHALL toggle the document theme state between light and dark modes and update the button's `aria-pressed` attribute accordingly

---

### Requirement: Login API Integration and Error Feedback
The login flow SHALL submit `{ email, password }` to `POST /api/v1/auth/login` using `fetch` with `credentials: "include"`, handle all documented OpenAPI responses (`200`, `401`, `422`, `429`, `502`, `503`) and network failures, and route the user according to `requires_onboarding`.

#### Scenario: Successful login with an existing business redirects to counter
- **GIVEN** an authenticated user account that already has an associated business (`requires_onboarding: false`)
- **WHEN** the user submits valid credentials and `POST /api/v1/auth/login` returns HTTP `200` with `user` and `business`
- **THEN** the application SHALL persist only public context metadata (`user`, `business_id`, business name, country, timezone, role) without storing any JWT or password, and SHALL redirect automatically to `/`

#### Scenario: Successful login without business opens blocking onboarding modal
- **GIVEN** an authenticated user account with no business yet (`requires_onboarding: true`, `business: null`)
- **WHEN** the user submits valid credentials and `POST /api/v1/auth/login` returns HTTP `200`
- **THEN** the application SHALL persist the authenticated user metadata without business context and SHALL render the accessible onboarding modal dialog instead of granting access to the operational counter

#### Scenario: Invalid credentials (401) show generic accessible error alert
- **GIVEN** the user submits incorrect credentials on `/login`
- **WHEN** `POST /api/v1/auth/login` responds with HTTP `401` and `ErrorResponse` (`code: "INVALID_CREDENTIALS"`)
- **THEN** the application SHALL remain on `/login`, SHALL NOT store session metadata, and SHALL display an accessible generic error message in a `role="alert"` region

#### Scenario: Validation (422), rate limit (429), and upstream errors (502/503/network) show accessible feedback
- **GIVEN** the user submits the login form
- **WHEN** `POST /api/v1/auth/login` returns HTTP `422`, `429`, `502`, `503` (with `ErrorResponse`), or fails due to network unavailability
- **THEN** the application SHALL exit loading state, retain the typed email without clearing it, and announce a clear, user-friendly error message inside a `role="alert"` region

---

### Requirement: Accessible Business Onboarding Modal
When an authenticated user has `requires_onboarding: true`, the application SHALL display a modal dialog (`role="dialog"`, `aria-modal="true"`) matching `onboarding-modal` in `docs/ui/auth-onboarding-ui-spec.json` (states: `ready`, `loading`, `error`) to register their unique business via `POST /api/v1/auth/onboarding`.

#### Scenario: Onboarding modal renders semantic fields and country options
- **GIVEN** an authenticated user with `requires_onboarding: true`
- **WHEN** the onboarding modal opens
- **THEN** the UI SHALL present an accessible dialog (`role="dialog"`, `aria-modal="true"`) with level-2 heading `"¡Bienvenido! Configura tu comercio"`, description `"Para comenzar a registrar ventas, indica el nombre de tu negocio y tu país de operación."`, required textbox `"Nombre del negocio"` (placeholder `"Ej. Kiosco Central"`, maxLength `100`), required combobox `"País de operación"` populated from the supported countries catalog with description `"Determina la moneda y la zona horaria de tus cierres de caja."`, and submit button `"Crear Comercio y Entrar"`

#### Scenario: Client-side validation rejects blank business name, over-length name, or missing country
- **GIVEN** the onboarding modal is open
- **WHEN** the user submits with a whitespace-only business name, a name exceeding 100 characters, or without selecting a country
- **THEN** the application SHALL NOT call `POST /api/v1/auth/onboarding`, SHALL mark invalid input(s) with `aria-invalid="true"`, and SHALL render an accessible message in a `role="alert"` region inside the dialog

#### Scenario: Successful onboarding (201) updates context and redirects to counter
- **GIVEN** the onboarding modal is open with a valid business name and supported country code
- **WHEN** the user submits `"Crear Comercio y Entrar"` and `POST /api/v1/auth/onboarding` responds HTTP `201` with `BusinessResponse`
- **THEN** the application SHALL update client public metadata with the created `business` (`id`, `name`, `country`, `timezone`, `role`), close the modal, and redirect automatically to `/`

#### Scenario: Duplicate business conflict (409) reconciles session or shows alert
- **GIVEN** the onboarding modal is open
- **WHEN** `POST /api/v1/auth/onboarding` responds HTTP `409` (`BUSINESS_ALREADY_EXISTS`)
- **THEN** the application SHALL invoke `GET /api/v1/auth/me` to reconcile state; if an active business is returned, it SHALL update context and navigate to `/`, otherwise it SHALL display the conflict message in a `role="alert"` element inside the modal

#### Scenario: Unauthenticated onboarding (401) attempts refresh before falling back to login
- **GIVEN** the onboarding modal is open and the access cookie expired
- **WHEN** `POST /api/v1/auth/onboarding` returns HTTP `401`
- **THEN** the application SHALL attempt `POST /api/v1/auth/refresh` once; if refresh succeeds (`200`), it SHALL display guidance to retry or continue, and if refresh fails (`401`), it SHALL clear stored public metadata and redirect to `/login` with a session-expired alert

#### Scenario: Onboarding modal cannot be bypassed to enter operational counter without a business
- **GIVEN** an authenticated user with `requires_onboarding: true`
- **WHEN** the user presses `Escape` or attempts to navigate directly to `/`
- **THEN** the application SHALL NOT grant access to the operational counter without a business, keeping the onboarding dialog active (offering only completion or explicit logout)

---

### Requirement: HttpOnly Cookie Session Management, Rehydration, Route Guards, and Logout
The application SHALL delegate session authentication exclusively to backend-managed `HttpOnly; SameSite=Strict` cookies (`credentials: "include"`), MUST NEVER persist JWTs, tokens, or credentials in `localStorage`, `sessionStorage`, or IndexedDB, and SHALL rehydrate and protect routes on navigation and reload.

#### Scenario: Only non-sensitive public metadata is stored in localStorage
- **GIVEN** a user completes login or onboarding
- **WHEN** inspecting browser `localStorage` and `sessionStorage`
- **THEN** stored client state SHALL contain only public context metadata (`user.id`, `user.email`, `business_id`, `business_name`, `country`, `timezone`, `role`, `requires_onboarding`) and MUST NOT contain `access_token`, `refresh_token`, raw JWT strings, or passwords

#### Scenario: App bootstrap on protected route rehydrates session via /api/v1/auth/me
- **GIVEN** a user reloads or visits `/` with a valid `HttpOnly` session cookie
- **WHEN** the application mounts and executes `GET /api/v1/auth/me` with `credentials: "include"` receiving HTTP `200` (`requires_onboarding: false`)
- **THEN** the application SHALL preserve the level-1 heading `"registro-venta-micro"` from initial render, synchronize public context metadata, and render the authenticated counter shell showing the active business name, user email, and a `"Cerrar sesión"` button

#### Scenario: Expired access cookie on /me triggers silent refresh before redirecting to /login
- **GIVEN** a user visits `/` with an expired `access_token` cookie
- **WHEN** `GET /api/v1/auth/me` returns HTTP `401`
- **THEN** the application SHALL call `POST /api/v1/auth/refresh` with `credentials: "include"`; on HTTP `200` it SHALL restore the session and allow access (or open onboarding if `requires_onboarding: true`), and on HTTP `401` it SHALL clear client metadata and redirect to `/login`

#### Scenario: Authenticated user visiting /login is redirected automatically to /
- **GIVEN** an authenticated user with an active business (`requires_onboarding: false`)
- **WHEN** the user navigates to `/login`
- **THEN** the application SHALL redirect automatically to `/`

#### Scenario: Logout clears session cookies and client metadata
- **GIVEN** an authenticated user on `/` (or inside the onboarding flow)
- **WHEN** the user activates the `"Cerrar sesión"` button
- **THEN** the application SHALL send `POST /api/v1/auth/logout` with `credentials: "include"`, remove all stored auth context metadata from `localStorage` and query cache, and redirect to `/login`

---

### Requirement: Critical End-to-End Authentication and Onboarding Journey
The application SHALL support the complete end-to-end user journey from unauthenticated entry at `/` through login, first-access onboarding, session persistence across reload, and logout in a headless browser.

#### Scenario: Unauthenticated user logs in, completes onboarding, reloads, and logs out
- **GIVEN** an unauthenticated browser session opening `/`
- **WHEN** the user is redirected to `/login`, signs in with credentials requiring onboarding, fills `"Kiosco Central"` and `"AR"` in the onboarding modal, submits `"Crear Comercio y Entrar"`, reloads `/`, and finally clicks `"Cerrar sesión"`
- **THEN** the browser SHALL transition `/ -> /login -> onboarding modal -> /` showing `"Kiosco Central"`, SHALL remain authenticated on `/` after page reload, and SHALL return to `/login` with empty `localStorage` auth context after logout

