# Modelo de Datos Consolidado (`registro-venta-micro`)

Diagrama Entidad-Relación (ERD) del esquema operativo en PostgreSQL 17 (Alembic aplicado: `d4e7f1a2b9c3`; incluye diseño consolidado `US-03-T06` para `sales`, `sale_items` y `payments` en `openspec/specs/sales-schema-and-rls/spec.md` y `openspec/changes/archive/2026-11-19-us-03-t06-esquema-ventas-rls-db`).  
Todas las tablas operativas están protegidas con `ENABLE` y `FORCE ROW LEVEL SECURITY` usando `app.current_business_id` (y `app.current_user_id` en `business_users` / `businesses` durante login y onboarding).

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#1e293b', 'primaryTextColor': '#ffffff', 'primaryBorderColor': '#38bdf8', 'lineColor': '#94a3b8' }}}%%
erDiagram
    BUSINESSES ||--o{ BUSINESS_USERS : "has members"
    BUSINESSES ||--o{ PRODUCTS : "owns catalog"
    BUSINESSES ||--o{ SALES : "records sales"
    SALES ||--|{ SALE_ITEMS : "contains lines"
    SALES ||--|{ PAYMENTS : "settled by"
    PRODUCTS ||--o{ SALE_ITEMS : "frozen into (RESTRICT)"

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

    SALES {
        uuid id PK "default gen_random_uuid()"
        uuid business_id FK, UK "NOT NULL, references businesses(id) ON DELETE CASCADE, uq(business_id, id)"
        uuid client_id UK "NOT NULL, uq_sales_business_id_client_id (business_id, client_id)"
        numeric_12_2 total_amount "NOT NULL, CHECK (total_amount > 0)"
        timestamptz created_at "NOT NULL, default now()"
    }

    SALE_ITEMS {
        uuid id PK "default gen_random_uuid()"
        uuid business_id FK "NOT NULL, composite FK to sales and products"
        uuid sale_id FK "NOT NULL, FK(business_id, sale_id) -> sales(business_id, id) ON DELETE CASCADE"
        uuid product_id FK "NOT NULL, FK(business_id, product_id) -> products(business_id, id) ON DELETE RESTRICT"
        numeric_12_2 quantity "NOT NULL, CHECK (quantity > 0)"
        numeric_12_2 unit_price "NOT NULL, CHECK (unit_price > 0)"
        numeric_12_2 unit_cost "NOT NULL, CHECK (unit_cost >= 0)"
        timestamptz created_at "NOT NULL, default now()"
    }

    PAYMENTS {
        uuid id PK "default gen_random_uuid()"
        uuid business_id FK "NOT NULL, references businesses(id) ON DELETE CASCADE"
        uuid sale_id FK "NOT NULL, FK(business_id, sale_id) -> sales(business_id, id) ON DELETE CASCADE"
        varchar payment_method "NOT NULL, CHECK IN ('cash', 'card', 'transfer')"
        numeric_12_2 amount "NOT NULL, CHECK (amount > 0)"
        timestamptz created_at "NOT NULL, default now()"
    }
```

## Convenciones transversales
- **Identificadores:** `UUID` generados con `gen_random_uuid()` y claves únicas compuestas `(business_id, id)` en tablas operativas padre (`products`, `sales`) para soportar FKs compuestas entre tablas del mismo negocio.
- **Montos, cantidades y stock:** `numeric(12,2)` (prohibido `float` / `double precision`).
- **Fechas:** `timestamptz` en UTC (agrupación diaria mediante `timezone` del comercio).
- **Seguridad:** `REVOKE ALL` a `PUBLIC, anon, authenticated` y `GRANT SELECT, INSERT, UPDATE, DELETE` a `app_api` (heredado por `app_runtime` con `NOBYPASSRLS`).
