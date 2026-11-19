# Delta Spec: businesses-schema-and-rls (Hardening Issue #54)

## ADDED Requirements

### Requirement: Endurecimiento de INSERT en businesses durante onboarding
La política `businesses_onboarding_insert` SHALL exigir que `app.current_user_id` esté configurado y no sea nulo, y que `id` coincida exactamente con `app.current_business_id`.

#### Scenario: Rechazo de INSERT en businesses sin contexto de usuario o negocio
- **WHEN** el rol `app_api` intenta `INSERT INTO businesses` sin `app.current_user_id` o sin `app.current_business_id` (o con un `id` distinto al GUC)
- **THEN** PostgreSQL rechaza la operación con SQLSTATE `42501` (insufficient_privilege / RLS violation).

#### Scenario: Permitir INSERT en businesses con contexto de onboarding válido
- **WHEN** el rol `app_api` tiene `app.current_user_id` y `app.current_business_id` seteados y ejecuta `INSERT INTO businesses (id, ...)` con `id = app.current_business_id`
- **THEN** la inserción es permitida.

### Requirement: Endurecimiento de INSERT, UPDATE y DELETE en business_users
La política `business_users_insert_own_user` SHALL exigir `app.current_business_id` no nulo y coincidente con `business_id` además de `user_id = app.current_user_id`. Las políticas de `UPDATE` y `DELETE` SHALL impedir modificaciones si `app.current_user_role` está seteado con un valor distinto de `'owner'`.

#### Scenario: Rechazo de INSERT en business_users sin app.current_business_id
- **WHEN** `app_api` tiene `app.current_user_id` seteado pero `app.current_business_id` está vacío o nulo e intenta insertar en `business_users`
- **THEN** PostgreSQL rechaza la operación con SQLSTATE `42501`.

#### Scenario: Rechazo de UPDATE/DELETE en business_users para rol cashier
- **WHEN** `app_api` tiene `app.current_business_id` seteado y `app.current_user_role = 'cashier'`
- **THEN** cualquier `UPDATE` o `DELETE` sobre `business_users` afecta 0 filas o es rechazado por RLS.

### Requirement: Revocación de privilegios a PUBLIC, anon y authenticated
Las tablas `businesses` y `business_users` SHALL revocar todos los privilegios (`REVOKE ALL`) de `PUBLIC`, `anon` y `authenticated`, evitando accesos directos vía PostgREST o `TRUNCATE`.

#### Scenario: Bloqueo de TRUNCATE y DML para authenticated
- **WHEN** el rol `authenticated` intenta `TRUNCATE businesses`, `TRUNCATE business_users` o `INSERT/SELECT` sobre dichas tablas
- **THEN** PostgreSQL rechaza la operación con SQLSTATE `42501`.

### Requirement: Rol runtime dedicado sin BYPASSRLS
La base de datos SHALL contar con un rol `app_runtime` con `LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE`, miembro de `app_api`, para evitar conexiones fail-open en runtime.

#### Scenario: Verificación de atributos y aislamiento de app_runtime
- **WHEN** se consulta `pg_roles` para `app_runtime` y se ejecutan consultas bajo `app_runtime` sin `SET LOCAL ROLE`
- **THEN** `rolcanlogin = true`, `rolsuper = false`, `rolbypassrls = false`, es miembro de `app_api`, y no puede omitir RLS ni ejecutar `TRUNCATE`.

### Requirement: Actualización automática de updated_at en businesses
La tabla `businesses` SHALL actualizar automáticamente `updated_at` mediante trigger `BEFORE UPDATE`.

#### Scenario: Actualización de updated_at al modificar un comercio
- **WHEN** se ejecuta `UPDATE businesses SET name = ...`
- **THEN** `updated_at` toma un timestamp mayor o igual al de la transacción actual, superando el valor previo.
