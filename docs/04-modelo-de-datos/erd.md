# Modelo de Datos Consolidado (`registro-venta-micro`)

Diagrama Entidad-Relación (ERD) del esquema operativo en PostgreSQL 17 (Alembic `head`: `a3f9d2e1b4c8`).  
Todas las tablas operativas están protegidas con `ENABLE` y `FORCE ROW LEVEL SECURITY` usando `app.current_business_id` (y `app.current_user_id` en `business_users` / `businesses` durante login y onboarding).

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#1e293b', 'primaryTextColor': '#ffffff', 'primaryBorderColor': '#38bdf8', 'lineColor': '#94a3b8' }}}%%
erDiagram
    BUSINESSES ||--o{ BUSINESS_USERS : "has members"
    BUSINESSES ||--o{ PRODUCTS : "owns catalog"

    BUSINESSES {
        uuid id PK "default gen_random_uuid()"
        varchar name "NOT NULL, len <= 100"
        varchar country "NOT NULL, len = 2"
        varchar timezone "NOT NULL, len <= 50"
        timestamptz created_at "NOT NULL, default now()"
        timestamptz updated_at "NOT NULL, default now()"
    }

    BUSINESS_USERS {
        uuid business_id PK, FK "references businesses(id) ON DELETE CASCADE"
        uuid user_id PK, UK "Supabase Auth user UUID (uq_business_users_user_id)"
        varchar role "NOT NULL, CHECK (role IN ('owner', 'cashier'))"
        timestamptz created_at "NOT NULL, default now()"
    }

    PRODUCTS {
        uuid id PK "default gen_random_uuid()"
        uuid business_id FK, UK "NOT NULL, references businesses(id) ON DELETE CASCADE, uq(business_id, id)"
        varchar code "NULL, len <= 50, partial UK(business_id, code) WHERE code IS NOT NULL"
        varchar name "NOT NULL, len <= 150"
        numeric_12_2 sale_price "NOT NULL, CHECK (sale_price > 0)"
        numeric_12_2 cost_price "NOT NULL, default 0, CHECK (cost_price >= 0)"
        numeric_12_2 stock "NOT NULL, default 0"
        boolean is_active "NOT NULL, default true"
        timestamptz created_at "NOT NULL, default now()"
        timestamptz updated_at "NOT NULL, default now() + trigger"
    }
```

## Convenciones transversales
- **Identificadores:** `UUID` generados con `gen_random_uuid()` y claves únicas compuestas `(business_id, id)` en tablas operativas para soportar FKs compuestas entre tablas del mismo negocio.
- **Montos y stock:** `numeric(12,2)` (prohibido `float` / `double precision`).
- **Fechas:** `timestamptz` en UTC.
- **Seguridad:** `REVOKE ALL` a `PUBLIC, anon, authenticated` y `GRANT SELECT, INSERT, UPDATE, DELETE` a `app_api` (heredado por `app_runtime` con `NOBYPASSRLS`).
