<!--
Ticket: US-01-T01 | Issue: #39 (https://github.com/ninargue/registro-venta-micro/issues/39) | Capa: db
-->

## Why

El sistema `registro-venta-micro` es una plataforma multitenant basada en PostgreSQL donde el aislamiento se garantiza mediante Row-Level Security (RLS). Actualmente el repositorio cuenta únicamente con la migración baseline vacía (`20261102_0001-ba617f3a8caa_baseline.py`). Para permitir el registro de usuarios, aprovisionamiento de negocios y la asignación del contexto de seguridad `app.current_business_id`, es indispensable crear las tablas `businesses` y `business_users`, estableciendo sus restricciones de integridad y políticas RLS como contrato fundacional.

## What Changes

- **Tabla `businesses`**: Entidad principal de negocio con `id` (UUID v4), `name` (`varchar(100)` NOT NULL), `country` (`varchar(2)` NOT NULL), `timezone` (`varchar(50)` NOT NULL, ej. `America/Argentina/Buenos_Aires`), `created_at` (`timestamptz`), `updated_at` (`timestamptz`).
- **Tabla `business_users`**: Asociación usuario-comercio con `business_id` (FK a `businesses.id`), `user_id` (UUID correspondiente al usuario de Supabase Auth / sesión), `role` (`varchar(20)` NOT NULL, ej. `'owner'`, `'cashier'`), `created_at` (`timestamptz`), con restricción `PRIMARY KEY (business_id, user_id)`.
- **Políticas RLS en `businesses` y `business_users`**:
  - Habilitación de `ROW LEVEL SECURITY` y `FORCE ROW LEVEL SECURITY`.
  - Política de aislamiento basada en la variable de configuración `app.current_business_id`: un usuario solo puede consultar o modificar el negocio activo configurado en su sesión de base de datos.
  - Bypass controlado para operaciones de creación/onboarding inicial cuando corresponda.
- **Migración Alembic**: Generación de la migración en `backend/migrations/versions/` con scripts reversibles (`upgrade` y `downgrade`).
- **Non-goals**: No incluye tablas de productos ni catálogo (corresponden a [Issue #42: US-02-T03](https://github.com/ninargue/registro-venta-micro/issues/42)), ni ventas (corresponden a [Issue #46: US-03-T06](https://github.com/ninargue/registro-venta-micro/issues/46)).

## Capabilities

### New Capabilities
- `businesses-schema-and-rls`: Esquema relacional para comercios, membresías de usuario con roles y políticas de seguridad RLS impuestas por `app.current_business_id`.

### Modified Capabilities
*(Ninguna - primer esquema operativo de base de datos tras la migración baseline)*

## Impact

- **Base de Datos**: Creación de las tablas `businesses` y `business_users` en PostgreSQL.
- **Migraciones**: Nueva versión de Alembic en `backend/migrations/versions/`.
- **Desbloqueo**: Provee la base requerida para el backend de Auth ([Issue #39: US-01-T01](https://github.com/ninargue/registro-venta-micro/issues/39)) y habilita la creación de la clave foránea `business_id` en la tabla `products` ([Issue #42: US-02-T03](https://github.com/ninargue/registro-venta-micro/issues/42)).
