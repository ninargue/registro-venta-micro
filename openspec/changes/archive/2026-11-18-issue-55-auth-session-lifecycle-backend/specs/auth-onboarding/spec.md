# Delta Spec: auth-onboarding (Issue #55)

## ADDED Requirements

### Requirement: Consulta de sesión activa (`GET /api/v1/auth/me`)
El endpoint `GET /api/v1/auth/me` SHALL validar la cookie `access_token` mediante `get_current_user` y retornar el estado de sesión del usuario autenticado (`user`, `requires_onboarding`, `business`).

#### Scenario: Consulta de sesión válida con comercio asignado
- **WHEN** un cliente envía `GET /api/v1/auth/me` con una cookie `access_token` válida
- **THEN** el backend responde `200` con `user`, `requires_onboarding = false` y los datos de `business` (o `requires_onboarding = true` y `business = null` si aún no hizo onboarding).

#### Scenario: Consulta sin sesión o con token inválido/expirado
- **WHEN** un cliente envía `GET /api/v1/auth/me` sin cookie `access_token` o con un JWT inválido/expirado/refresh
- **THEN** el backend responde `401` con formato `ErrorResponse` (`code = "UNAUTHENTICATED"`).

### Requirement: Cierre de sesión (`POST /api/v1/auth/logout`)
El endpoint `POST /api/v1/auth/logout` SHALL limpiar las cookies `access_token` y `refresh_token` (`Max-Age=0`) respetando los atributos `HttpOnly`, `SameSite=Strict`, `Secure` (`COOKIE_SECURE`) y `path="/"`.

#### Scenario: Logout limpia ambas cookies de sesión
- **WHEN** se envía `POST /api/v1/auth/logout`
- **THEN** el backend responde `204` e incluye headers `Set-Cookie` que expiran `access_token` y `refresh_token` (`Max-Age=0`, `HttpOnly`, `SameSite=Strict`).

### Requirement: Renovación de sesión (`POST /api/v1/auth/refresh`)
El endpoint `POST /api/v1/auth/refresh` SHALL validar la cookie `refresh_token` (`token_type = "refresh"`), consultar la membresía actual bajo RLS, emitir nuevas cookies `access_token` y `refresh_token`, y retornar `200` con `LoginResponse`.

#### Scenario: Refresh exitoso con cookie refresh_token válida
- **WHEN** un cliente envía `POST /api/v1/auth/refresh` con una cookie `refresh_token` válida
- **THEN** el backend responde `200` con `LoginResponse` y emite nuevas cookies `access_token` y `refresh_token` `HttpOnly`.

#### Scenario: Refresh rechazado si falta cookie, está expirada o es un access_token
- **WHEN** un cliente envía `POST /api/v1/auth/refresh` sin cookie `refresh_token`, con un JWT expirado o con un `access_token`
- **THEN** el backend responde `401` con `ErrorResponse` (`code = "UNAUTHENTICATED"`) sin emitir cookies.
