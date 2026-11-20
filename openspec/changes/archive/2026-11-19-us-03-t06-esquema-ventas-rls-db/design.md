## Context

El sistema `registro-venta-micro` implementa aislamiento multitenant estricto en PostgreSQL 17 mediante Row-Level Security (RLS) forzada sobre todas las tablas operativas, utilizando la variable de sesión transaccional `SET LOCAL app.current_business_id = '<uuid>'` inyectada por FastAPI (`get_tenant_db`) bajo el rol de runtime sin privilegios `app_runtime` (miembro de `app_api`, `NOBYPASSRLS`).

Las migraciones `0002`–`0005` establecieron las tablas `businesses`, `business_users` y `products` (incluyendo la clave alternativa compuesta `uq_products_business_id_id` sobre `(business_id, id)` preparada específicamente para las claves foráneas compuestas de ventas), el rol `app_runtime` y el patrón de RLS granular por operación y DCL de mínimo privilegio. Este cambio (`us-03-t06-esquema-ventas-rls-db`, Ticket `US-03-T06` / Issue `#46`) introduce las tablas transaccionales `sales`, `sale_items` y `payments` para habilitar ventas multimedio con precio/costo congelados, idempotencia por negocio `(business_id, client_id)` y reporte diario por zona horaria local.

### Convenciones e Infraestructura Detectada

```yaml
engine: "postgres"
migrations_dir: "backend/migrations"
security_dir: "backend/migrations"
seeds_dir: "none"
tests_dir: "backend/tests"
tests_domain_convention: "backend/tests/integration/test_db_<dominio>.py"
migration_mode: "forward-only"
rls_mode: "in-situ"
requires_seeds: false
test_cmd: "cd backend && uv run pytest"
validation_cmd: "cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy app"
sql_from_cmd: "cd backend && uv run alembic upgrade head --sql"
typecheck_cmd: "cd backend && uv run mypy app"
up_cmd: "cd backend && uv run alembic upgrade head"
down_cmd: "cd backend && uv run alembic downgrade -1"
snapshot_cmd: "none"
schemas_dir: "docs/04-modelo-de-datos"
```

> **Notas operativas del repositorio**:
> - Las migraciones viven en Alembic Python (`backend/migrations/versions/*.py`) con políticas RLS y DCL embebidas (`rls_mode: "in-situ"`). Se declara `migration_mode: "forward-only"` con `sql_from_cmd` para compatibilidad con `validate-db-migrations.js`; no obstante, la migración Python debe implementar `upgrade()` y `downgrade()` simétricos completos porque `.github/workflows/ci-backend.yml` exige `alembic check` y `alembic downgrade base && alembic upgrade head`.
> - En `backend/.env` / entorno local, `backend/migrations/env.py` lee `DATABASE_URL` desde `app.core.config.get_settings()` (incluso para `alembic upgrade head --sql`). Para aplicar migraciones y tests, `DB_TEST_URL` apunta a la base efímera de pruebas (`postgresql+asyncpg://postgres:postgres@127.0.0.1:54422/postgres_test`).
> - La columna de aislamiento multitenant en este repositorio es `business_id` (no `tenant_id`) y el GUC de sesión es `app.current_business_id` (no `app.tenant_id`).
> - Existe el ERD consolidado en `docs/04-modelo-de-datos/erd.md`.

## Goals / Non-Goals

**Goals:**
- Crear `public.sales` con `id` UUID PK, `business_id` (`FK -> businesses(id) ON DELETE CASCADE`), `client_id` UUID con unicidad compuesta `(business_id, client_id)` para idempotencia transaccional (`ON CONFLICT DO NOTHING`), `total_amount` (`numeric(12,2) > 0`), `created_at` (`timestamptz` UTC), clave única `(business_id, id)` e índice `(business_id, created_at)`.
- Crear `public.sale_items` con `id` UUID PK, `business_id`, `sale_id`, `product_id`, `quantity` (`numeric(12,2) > 0`), snapshot congelado `unit_price` (`numeric(12,2) > 0`) y `unit_cost` (`numeric(12,2) >= 0`), `created_at` (`timestamptz`), y FKs compuestas `(business_id, sale_id) -> sales(business_id, id) ON DELETE CASCADE` y `(business_id, product_id) -> products(business_id, id) ON DELETE RESTRICT`.
- Crear `public.payments` con `id` UUID PK, `business_id`, `sale_id`, `payment_method` (`varchar(20)` con `CHECK IN ('cash', 'card', 'transfer')`), `amount` (`numeric(12,2) > 0`), `created_at` (`timestamptz`), y FK compuesta `(business_id, sale_id) -> sales(business_id, id) ON DELETE CASCADE`.
- Habilitar y forzar RLS (`ENABLE` + `FORCE ROW LEVEL SECURITY`) en `sales`, `sale_items` y `payments` con políticas granulares (`SELECT`, `INSERT`, `UPDATE` con `USING`+`WITH CHECK`, `DELETE`) filtradas por `app.current_business_id`, revocando privilegios a `PUBLIC`/`anon`/`authenticated` y otorgando DML exclusivo (sin `TRUNCATE`) a `app_api` / `app_runtime`.
- Sincronizar modelos SQLAlchemy `Sale`, `SaleItem`, `Payment` en `backend/app/modules/sales/models.py` + `backend/app/db/base.py` para mantener `alembic check` en verde.

**Non-Goals:**
- Endpoints REST (`POST /api/v1/sales`, `GET /api/v1/reports/daily`), servicio transaccional con descuento atómico de stock (`stock = stock - quantity`) o validación cruzada de suma de `payments.amount == sales.total_amount` (corresponden a `#47` / `TICKET-07` y `#50` / `TICKET-09`).
- Vistas o calculador de vuelto en frontend (`#48` / `TICKET-08` y `#51` / `TICKET-10`).
- Entidades excluidas del MVP acotado (`docs/prd/0001_alcance_mvp.md` §5): `cash_sessions`, `stock_movements`, anulaciones/notas de crédito, descuentos, impuestos o `updated_at` en tablas transaccionales inmutables.

## Estado observado de la base

- **Fecha de inspección**: `2026-11-19`
- **Disponibilidad de `DB_DEV_RO_URL`**: **No configurada en este entorno** (`DB_DEV_RO_URL` está vacía en entorno y comentada en `backend/.env`). No se utilizó `DATABASE_URL`/`DB_DEV_URL` ni credenciales de escritura durante la fase de exploración.
- **Fuente inspeccionada**: Repositorio del worktree (`backend/migrations/versions/20261102_0001-...` hasta `20261118_0005-a3f9d2e1b4c8_create_products_table.py`, `backend/app/modules/auth/models.py`, `backend/app/modules/catalog/models.py`, `backend/app/db/base.py`, `backend/app/core/db.py`, `docs/04-modelo-de-datos/erd.md` y reporte de verificación previo `openspec/changes/archive/2026-11-19-issue-42-esquema-productos-db/verification-report.md`).
- **Revisión Alembic activa (`head`)**: `a3f9d2e1b4c8` (`20261118_0005-a3f9d2e1b4c8_create_products_table.py`).
- **Tablas existentes en `public`**:
  - `alembic_version` (control de versiones Alembic).
  - `businesses` (PK `id`, trigger `trg_businesses_set_updated_at`, RLS `ENABLE`+`FORCE`).
  - `business_users` (PK `(business_id, user_id)`, `uq_business_users_user_id`, RLS `ENABLE`+`FORCE`).
  - `products` (PK `id`, `uq_products_business_id_id` `UNIQUE (business_id, id)`, `uq_products_business_id_code`, `ix_products_business_id_active_name`, `sale_price`/`cost_price`/`stock` en `numeric(12,2)`, trigger `trg_products_set_updated_at`, RLS `ENABLE`+`FORCE`).
  - `sales`, `sale_items`, `payments`: **no existen** todavía (tablas nuevas).
- **Roles y seguridad vigentes**: `app_api` (`NOLOGIN`, `NOSUPERUSER`, `NOBYPASSRLS`) con `GRANT SELECT, INSERT, UPDATE, DELETE` sobre `businesses`, `business_users` y `products`; `app_runtime` (`LOGIN`, `NOSUPERUSER`, `NOBYPASSRLS`, miembro de `app_api`); `PUBLIC`, `anon` y `authenticated` sin privilegios sobre tablas operativas.
- **Módulo ORM `sales`**: `backend/app/modules/sales/__init__.py` vacío; `backend/app/db/base.py` importa únicamente `Business`, `BusinessUser` y `Product`.

## Reversibilidad

> **Nota sobre conteo de filas**: `DB_DEV_RO_URL` no está configurada en este entorno (`2026-11-19`); todas las entidades introducidas por este cambio son tablas nuevas (`0` filas previas).

| Operación | Tablas | Filas reales (vía RO + fecha) | Clasificación | Rollback / Compensatoria |
|---|---|---|---|---|
| `CREATE TABLE sales` (PK, FK `businesses`, `uq_sales_business_id_id`, `uq_sales_business_id_client_id`, `CHECK total_amount > 0`) e índice `ix_sales_business_id_created_at` | `sales` | `0` *(tabla nueva)* | `reversible` | En `downgrade()`: revocar DCL, eliminar políticas RLS/deshabilitar RLS, `op.drop_index("ix_sales_business_id_created_at", ...)` y `op.drop_table("sales")` (después de eliminar `sale_items` y `payments`). |
| `CREATE TABLE sale_items` (PK, FKs a `businesses`, `sales(business_id, id)` y `products(business_id, id)`, `CHECK`s) e índices `ix_sale_items_business_id_sale_id`, `ix_sale_items_business_id_product_id` | `sale_items` | `0` *(tabla nueva)* | `reversible` | En `downgrade()`: revocar DCL, eliminar políticas RLS/deshabilitar RLS, eliminar índices y `op.drop_table("sale_items")` (antes de `sales`). |
| `CREATE TABLE payments` (PK, FKs a `businesses` y `sales(business_id, id)`, `CHECK`s) e índice `ix_payments_business_id_sale_id` | `payments` | `0` *(tabla nueva)* | `reversible` | En `downgrade()`: revocar DCL, eliminar políticas RLS/deshabilitar RLS, eliminar índice y `op.drop_table("payments")` (antes de `sales`). |
| `ENABLE` / `FORCE ROW LEVEL SECURITY`, 12 políticas granulares (4 por tabla) y DCL (`REVOKE ALL`, `GRANT SELECT, INSERT, UPDATE, DELETE TO app_api`) | `sales`, `sale_items`, `payments` | `0` *(tablas nuevas)* | `reversible` | `REVOKE ALL ... FROM app_api;`, `DROP POLICY IF EXISTS ...` y `NO FORCE` / `DISABLE ROW LEVEL SECURITY` en orden inverso antes de `DROP TABLE`. |

## Normalización

- Las tres tablas nuevas nacen en **Tercera Forma Normal (3NF)** (`0` filas previas; no aplica Expand / Contract):
  - `sales`: todos los atributos no clave (`business_id`, `client_id`, `total_amount`, `created_at`) dependen únicamente de `id` (y dentro del ámbito de `business_id` vía `(business_id, client_id)`).
  - `sale_items`: los snapshots históricos `unit_price` y `unit_cost` no violan 3NF porque representan los precios **vigentes en el instante de la venta**, independientes de futuras actualizaciones sobre `products.sale_price` y `products.cost_price`. Se omite intencionalmente la columna redundante/derivada `subtotal` (`round(quantity * unit_price, 2)`) para evitar anomalías de actualización y mantener 3NF estricta, ya que el MVP no contempla descuentos por línea.
  - `payments`: desglose atómico por medio de pago (`payment_method`, `amount`) dependiente de `id` y perteneciente a la venta `(business_id, sale_id)`.

## Decisions

1. **Unicidad compuesta `(business_id, client_id)` con `UUID` nativo en `sales` para idempotencia aislada por negocio**:
   - *Por qué*: `TICKET-06` exige clave única `(business_id, client_id)` y `TICKET-08` genera un UUID v4 en cliente por venta en preparación. Usar `UUID` nativo (`postgresql.UUID`) junto con `UniqueConstraint("business_id", "client_id", name="uq_sales_business_id_client_id")` habilita `INSERT ... ON CONFLICT (business_id, client_id) DO NOTHING` en `TICKET-07`, rechaza inserciones duplicadas directas con `23505`, e impide que un tenant B infiera o colisione con un `client_id` usado por el tenant A (evitando oráculos cross-tenant).
   - *Alternativa descartada*: Usar `client_id` como clave primaria global o `UNIQUE (client_id)` sin `business_id` (expondría colisiones cross-tenant y divergiría de la convención `id = gen_random_uuid()` + `(business_id, id)` de `docs/04-modelo-de-datos/erd.md`).

2. **Integridad referencial compuesta `(business_id, sale_id)` y `(business_id, product_id)` con `ON DELETE RESTRICT` en `products`**:
   - *Por qué*: Tanto `sale_items` como `payments` incluyen `business_id NOT NULL` (FK directa a `businesses(id) ON DELETE CASCADE` para RLS O(1) sin subconsultas ni `JOIN`s en políticas) y utilizan FKs compuestas contra `sales(business_id, id)` (`ON DELETE CASCADE`) y `products(business_id, id)` (`ON DELETE RESTRICT`). Esto garantiza a nivel de motor que una venta del negocio A jamás pueda asociar ítems o pagos de un producto o venta del negocio B. Adicionalmente, `ON DELETE RESTRICT` sobre `products` impide el borrado físico de productos con histórico de ventas (reforzando la baja lógica `is_active = false` definida en `#42` / ADR-0004), mientras que `ON DELETE CASCADE` desde `sales` elimina ordenadamente sus líneas y pagos hijos.
   - *Alternativa descartada*: FKs simples por `sale_id` / `product_id` sin `business_id` (permitirían inconsistencias referenciales cross-tenant si se omitiera RLS o bajo rol privilegiado), o `ON DELETE CASCADE` desde `products` hacia `sale_items` (destruiría silenciosamente el histórico contable).

3. **Precisión estricta `numeric(12,2)` en montos y cantidades (`quantity`, `unit_price`, `unit_cost`, `total_amount`, `amount`)**:
   - *Por qué*: El PRD v0.2 (§4 NFR 2), `TICKET-06` y la tabla `products` (`stock` en `numeric(12,2)`) exigen exactitud decimal sin `float`. Utilizar `numeric(12,2)` en `sale_items.quantity` alinea exactamente su escala con `products.stock` durante la deducción `stock = stock - quantity` en `TICKET-07`. Se imponen `CHECK (total_amount > 0)`, `CHECK (quantity > 0)`, `CHECK (unit_price > 0)`, `CHECK (unit_cost >= 0)` (permitiendo costo `0.00` igual que `products.cost_price`) y `CHECK (amount > 0)`.
   - *Alternativa descartada*: Usar `numeric(12,3)` de Entrega 1 en `quantity` (desalinearía la escala respecto a `products.stock = numeric(12,2)`).

4. **Catálogo de medios de pago `payment_method IN ('cash', 'card', 'transfer')` en `payments`**:
   - *Por qué*: `docs/prd/0001_alcance_mvp.md` (§4 F2/F3), `TICKET-08` y `us-04` (`TICKET-09`) definen exactamente tres medios de pago en el MVP (`Efectivo`, `Tarjeta`, `Transferencia / QR`), siguiendo la convención de literales en inglés minúscula del esquema (`owner`, `cashier`).
   - *Alternativa descartada*: Incluir `'other'` de Entrega 1 (crearía un cuarto cubo no contemplado en el desglose del reporte diario `us-04`) o usar tipo `ENUM` nativo de PostgreSQL (`CREATE TYPE`) que complica migraciones `ALTER TYPE` y sincronía con `alembic check`.

5. **Validación cruzada de suma de pagos (`SUM(payments.amount) == sales.total_amount`) en capa de servicio (`TICKET-07`), sin triggers diferidos en BD**:
   - *Por qué*: En una transacción de venta, la cabecera `sales` se inserta antes que sus hijos `sale_items` y `payments`. Un trigger inmediato bloquearía la inserción de `sales`, y un `CONSTRAINT TRIGGER INITIALLY DEFERRED` no dispara dentro de savepoints (`begin_nested()`) en tests unitarios de tabla e introduce acoplamiento prematuro. Siguiendo `TICKET-07` y `us-03`, el servidor valida en `Decimal` que la suma de ítems y la suma de pagos coincidan exactamente con `total_amount` dentro de la transacción ACID.
   - *Alternativa descartada*: `CONSTRAINT TRIGGER ... INITIALLY DEFERRED` entre 3 tablas.

6. **Índices compuestos liderados por `business_id` para consultas de ventas, reportes diarios (`TICKET-09`) y compatibilidad con `validate-db-migrations.js`**:
   - *Por qué*:
     - `sales`: `uq_sales_business_id_id` (`(business_id, id)`), `uq_sales_business_id_client_id` (`(business_id, client_id)`) e índice explícito `ix_sales_business_id_created_at` (`(business_id, created_at)`) para el consolidado diario `(created_at AT TIME ZONE b.timezone)::date = :fecha`.
     - `sale_items`: `ix_sale_items_business_id_sale_id` (`(business_id, sale_id)`) e `ix_sale_items_business_id_product_id` (`(business_id, product_id)`).
     - `payments`: `ix_payments_business_id_sale_id` (`(business_id, sale_id)`).
     Todos llevan `business_id` como columna líder, satisfacen la verificación `[INDEX FK]` de `validate-db-migrations.js` sobre las FKs `business_id`, cubren las FKs compuestas y evitan expresiones funcionales en `Index` que puedan generar falsos positivos en `alembic check`.
   - *Alternativa descartada*: Índice funcional sobre `(created_at AT TIME ZONE ...)` (imposible sobre otra tabla `businesses.timezone` e incompatible con funciones no `IMMUTABLE`) o `created_at DESC` si causa deriva en reflexión Alembic.

7. **Políticas RLS granulares, DCL mínimo privilegio y sincronización de modelos SQLAlchemy (`alembic check`)**:
   - *Por qué*: Se replica exactamente el estándar de `products` (`0005`): `ENABLE` + `FORCE ROW LEVEL SECURITY`, 4 políticas granulares (`SELECT`, `INSERT`, `UPDATE` con `USING`+`WITH CHECK`, `DELETE`) usando `NULLIF(current_setting('app.current_business_id', true), '')::uuid`, `REVOKE ALL` a `PUBLIC`/`anon`/`authenticated`, y `GRANT SELECT, INSERT, UPDATE, DELETE` a `app_api` (heredado por `app_runtime`). Simultáneamente se crean los modelos ORM `Sale`, `SaleItem`, `Payment` en `backend/app/modules/sales/models.py` y se importan en `backend/app/db/base.py` para que `uv run alembic check` pase en CI.
   - *Alternativa descartada*: Omitir políticas `UPDATE`/`DELETE` dejando `GRANT SELECT, INSERT, UPDATE, DELETE` (fallaría en `validate-db-migrations.js` `[RLS COBERTURA]`) o postergar los modelos ORM a `#47` (rompería `alembic check` en CI).

### Diagrama Entidad-Relación (ERD)

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#1e293b', 'primaryTextColor': '#ffffff', 'primaryBorderColor': '#38bdf8', 'lineColor': '#94a3b8' }}}%%
erDiagram
    BUSINESSES ||--o{ SALES : "records sales"
    BUSINESSES ||--o{ PRODUCTS : "owns catalog"
    SALES ||--|{ SALE_ITEMS : "contains lines"
    SALES ||--|{ PAYMENTS : "settled by"
    PRODUCTS ||--o{ SALE_ITEMS : "frozen into (RESTRICT)"

    BUSINESSES {
        uuid id PK
        varchar name "NOT NULL"
        varchar country "NOT NULL, len 2"
        varchar timezone "NOT NULL"
    }

    PRODUCTS {
        uuid id PK
        uuid business_id FK, UK "uq_products_business_id_id"
        varchar name "NOT NULL"
        numeric sale_price "12,2 > 0"
        numeric cost_price "12,2 >= 0"
        numeric stock "12,2"
        boolean is_active "DEFAULT true"
    }

    SALES {
        uuid id PK "default gen_random_uuid()"
        uuid business_id FK, UK "uq_sales_business_id_id"
        uuid client_id UK "uq_sales_business_id_client_id (business_id, client_id)"
        numeric total_amount "12,2 NOT NULL, CHECK > 0"
        timestamptz created_at "NOT NULL, default now()"
    }

    SALE_ITEMS {
        uuid id PK "default gen_random_uuid()"
        uuid business_id FK "composite FK to sales and products"
        uuid sale_id FK "ON DELETE CASCADE"
        uuid product_id FK "ON DELETE RESTRICT"
        numeric quantity "12,2 NOT NULL, CHECK > 0"
        numeric unit_price "12,2 NOT NULL, CHECK > 0 (frozen)"
        numeric unit_cost "12,2 NOT NULL, CHECK >= 0 (frozen)"
        timestamptz created_at "NOT NULL, default now()"
    }

    PAYMENTS {
        uuid id PK "default gen_random_uuid()"
        uuid business_id FK "composite FK to sales"
        uuid sale_id FK "ON DELETE CASCADE"
        varchar payment_method "NOT NULL, CHECK IN ('cash','card','transfer')"
        numeric amount "12,2 NOT NULL, CHECK > 0"
        timestamptz created_at "NOT NULL, default now()"
    }
```

### Diccionario Físico de Datos

#### Tabla: `public.sales`
| Columna | Tipo Nativo | Nulabilidad | Default | Constraints / Índices | Seguridad / Clasificación |
|---|---|---|---|---|---|
| `id` | `UUID` | `NOT NULL` | `gen_random_uuid()` | `PRIMARY KEY (id)` (`pk_sales`), `UNIQUE (business_id, id)` (`uq_sales_business_id_id`) | Identificador subrogado de venta |
| `business_id` | `UUID` | `NOT NULL` | - | `FK -> businesses(id) ON DELETE CASCADE` (`fk_sales_business_id`), líder en `uq_sales_business_id_id`, `uq_sales_business_id_client_id`, `ix_sales_business_id_created_at` | Clave de multi-tenancy (`app.current_business_id`) |
| `client_id` | `UUID` | `NOT NULL` | - | `UNIQUE (business_id, client_id)` (`uq_sales_business_id_client_id`) | Llave de idempotencia generada por el cliente |
| `total_amount` | `NUMERIC(12,2)` | `NOT NULL` | - | `CHECK (total_amount > 0)` (`chk_sales_total_amount_positive`) | Total bruto cobrado (`Decimal`, prohibido `float`) |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL` | `now()` | Indexado en `ix_sales_business_id_created_at (business_id, created_at)` | Fecha/hora UTC de registro (agrupada en reporte por `businesses.timezone`) |

#### Tabla: `public.sale_items`
| Columna | Tipo Nativo | Nulabilidad | Default | Constraints / Índices | Seguridad / Clasificación |
|---|---|---|---|---|---|
| `id` | `UUID` | `NOT NULL` | `gen_random_uuid()` | `PRIMARY KEY (id)` (`pk_sale_items`) | Identificador de línea de venta |
| `business_id` | `UUID` | `NOT NULL` | - | `FK -> businesses(id) ON DELETE CASCADE` (`fk_sale_items_business_id`), líder en `ix_sale_items_business_id_sale_id`, `ix_sale_items_business_id_product_id` | Clave de multi-tenancy (`app.current_business_id`) |
| `sale_id` | `UUID` | `NOT NULL` | - | `FK (business_id, sale_id) -> sales(business_id, id) ON DELETE CASCADE` (`fk_sale_items_sale`), indexado en `ix_sale_items_business_id_sale_id` | Venta padre aislada por comercio |
| `product_id` | `UUID` | `NOT NULL` | - | `FK (business_id, product_id) -> products(business_id, id) ON DELETE RESTRICT` (`fk_sale_items_product`), indexado en `ix_sale_items_business_id_product_id` | Producto vendido aislado por comercio (protege histórico) |
| `quantity` | `NUMERIC(12,2)` | `NOT NULL` | - | `CHECK (quantity > 0)` (`chk_sale_items_quantity_positive`) | Cantidad vendida (`Decimal`, escala alineada con `products.stock`) |
| `unit_price` | `NUMERIC(12,2)` | `NOT NULL` | - | `CHECK (unit_price > 0)` (`chk_sale_items_unit_price_positive`) | Snapshot congelado de precio de venta bruto |
| `unit_cost` | `NUMERIC(12,2)` | `NOT NULL` | - | `CHECK (unit_cost >= 0)` (`chk_sale_items_unit_cost_non_negative`) | Snapshot congelado de costo unitario para margen histórico |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL` | `now()` | - | Auditoría (UTC) |

#### Tabla: `public.payments`
| Columna | Tipo Nativo | Nulabilidad | Default | Constraints / Índices | Seguridad / Clasificación |
|---|---|---|---|---|---|
| `id` | `UUID` | `NOT NULL` | `gen_random_uuid()` | `PRIMARY KEY (id)` (`pk_payments`) | Identificador de registro de pago |
| `business_id` | `UUID` | `NOT NULL` | - | `FK -> businesses(id) ON DELETE CASCADE` (`fk_payments_business_id`), líder en `ix_payments_business_id_sale_id` | Clave de multi-tenancy (`app.current_business_id`) |
| `sale_id` | `UUID` | `NOT NULL` | - | `FK (business_id, sale_id) -> sales(business_id, id) ON DELETE CASCADE` (`fk_payments_sale`), indexado en `ix_payments_business_id_sale_id` | Venta padre aislada por comercio |
| `payment_method` | `VARCHAR(20)` | `NOT NULL` | - | `CHECK (payment_method IN ('cash', 'card', 'transfer'))` (`chk_payments_method_valid`) | Medio de pago MVP (sin datos de tarjeta ni PAN/CVV; sin PII) |
| `amount` | `NUMERIC(12,2)` | `NOT NULL` | - | `CHECK (amount > 0)` (`chk_payments_amount_positive`) | Monto neto imputado por ese medio (`Decimal`, prohibido `float`) |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL` | `now()` | - | Auditoría (UTC) |

### Estrategia de Seguridad RLS y DCL

1. **Activación y Forzado de RLS** (sobre `sales`, `sale_items` y `payments`):
   - `ALTER TABLE <table> ENABLE ROW LEVEL SECURITY;`
   - `ALTER TABLE <table> FORCE ROW LEVEL SECURITY;`
2. **Políticas Granulares por Operación** en cada tabla (`sales_*_isolation`, `sale_items_*_isolation`, `payments_*_isolation`), usando `NULLIF(current_setting('app.current_business_id', true), '')::uuid`:
   - `FOR SELECT`: `USING (business_id = NULLIF(current_setting('app.current_business_id', true), '')::uuid)`
   - `FOR INSERT`: `WITH CHECK (business_id = NULLIF(current_setting('app.current_business_id', true), '')::uuid)`
   - `FOR UPDATE`: `USING (business_id = NULLIF(current_setting('app.current_business_id', true), '')::uuid) WITH CHECK (business_id = NULLIF(current_setting('app.current_business_id', true), '')::uuid)`
   - `FOR DELETE`: `USING (business_id = NULLIF(current_setting('app.current_business_id', true), '')::uuid)`
3. **Privilegios DCL (Mínimo Privilegio)**:
   - `REVOKE ALL ON TABLE sales FROM PUBLIC, anon, authenticated;`
   - `REVOKE ALL ON TABLE sale_items FROM PUBLIC, anon, authenticated;`
   - `REVOKE ALL ON TABLE payments FROM PUBLIC, anon, authenticated;`
   - `GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE sales TO app_api;`
   - `GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE sale_items TO app_api;`
   - `GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE payments TO app_api;`
   *(Sin `TRUNCATE`, heredado por `app_runtime` con `rolsuper = false` y `rolbypassrls = false`, manteniendo propiedad en `postgres`).*

### Contratos de Modelos ORM y Errores de BD Esperados

- **Modelos SQLAlchemy (`backend/app/modules/sales/models.py`)**:
  - `Sale(Base)`: `__tablename__ = "sales"`, atributos tipados `Mapped[uuid.UUID]`, `Mapped[Decimal]`, `Mapped[datetime]` con `Numeric(12, 2)` y `UUID(as_uuid=True)`.
  - `SaleItem(Base)`: `__tablename__ = "sale_items"`, mismas convenciones + FKs compuestas declaradas explícitamente en `__table_args__`.
  - `Payment(Base)`: `__tablename__ = "payments"`, mismas convenciones + FK compuesta declarada en `__table_args__`.
  - Exportar e importar los tres modelos en `backend/app/db/base.py`.
- **Errores PostgreSQL observables por la capa API (`#47`)**:
  - `23505` (`uq_sales_business_id_client_id`): conflicto de idempotencia ante doble `INSERT` sin `ON CONFLICT` (o resuelto silenciosamente mediante `INSERT ... ON CONFLICT (business_id, client_id) DO NOTHING`).
  - `23503`: referencia inexistente o cross-tenant en `(business_id, sale_id)` / `(business_id, product_id)`, o intento de `DELETE FROM products` con ventas históricas.
  - `23514`: violación de `total_amount > 0`, `quantity > 0`, `unit_price > 0`, `unit_cost >= 0`, `amount > 0` o `payment_method` inválido.
  - `42501`: violación RLS (inserción/actualización cross-tenant o sin contexto `app.current_business_id`) o intento de `TRUNCATE`/acceso por `PUBLIC`/`anon`/`authenticated`.

## Risks / Trade-offs

- **[Risk] `DELETE FROM businesses` cuando existen `sale_items` referenciando `products` con `ON DELETE RESTRICT` falla con `23503`** → **Mitigación**: Es el comportamiento esperado para proteger la inmutabilidad del histórico de ventas frente a `products` (`is_active = false`); para eliminar un negocio de prueba con ventas, primero se eliminan sus `sales` (que hacen `CASCADE` a `sale_items` y `payments`) o se limpian en orden hijo→padre en tests.
- **[Risk] Inconsistencia de suma `SUM(payments.amount) != sales.total_amount` ante inserción directa en SQL fuera de `TICKET-07`** → **Mitigación**: La consistencia entre totales de cabecera, líneas y pagos es responsabilidad atómica del servicio transaccional `POST /api/v1/sales` (`#47` / `TICKET-07`) en `Decimal`, evitando triggers diferidos rígidos que entorpezcan pruebas unitarias de BD.
- **[Risk] Deriva entre `alembic check` y FKs compuestas / nombres de constraints en SQLAlchemy** → **Mitigación**: Declarar todos los nombres de `PrimaryKeyConstraint`, `ForeignKeyConstraint`, `UniqueConstraint`, `CheckConstraint` e `Index` de forma idéntica en `models.py` y en la migración Alembic, validando con `uv run alembic check` contra `DB_TEST_URL`.
- **[Risk] Exploración sin `DB_DEV_RO_URL` configurado en el worktree** → **Mitigación**: Estado observado verificado estáticamente contra las migraciones versionadas (`0001`–`0005`), `models.py` y `verification-report.md` de `#42`; en los pasos siguientes se validará en vivo contra la base efímera `DB_TEST_URL`.

## Migration Plan

1. **Suite DB-TDD en ROJO (`backend/tests/integration/test_db_sales.py`)**: Cubrir estructura y tipos `numeric(12,2)` (sin `float`), idempotencia `(business_id, client_id)` (tanto rechazo `23505` como `INSERT ... ON CONFLICT DO NOTHING` y aislamiento entre negocios), snapshots congelados de `unit_price`/`unit_cost`, FKs compuestas cross-tenant (`23503`), `ON DELETE RESTRICT` en `products` vs `ON DELETE CASCADE` desde `sales`, `CHECK`s de dominio, aislamiento RLS granular en las 4 operaciones bajo `app_runtime` y DCL mínimo privilegio / bloqueo `TRUNCATE`.
2. **Modelos ORM (`backend/app/modules/sales/models.py` + `backend/app/db/base.py`)**: Definir `Sale`, `SaleItem` y `Payment` con `Decimal` / `Numeric(12, 2)`, constraints e índices alineados al diccionario físico.
3. **Nueva Migración Alembic (`down_revision = "a3f9d2e1b4c8"`)**: Crear tablas `sales`, `sale_items` y `payments`, sus FKs compuestas, índices liderados por `business_id`, `ENABLE`/`FORCE ROW LEVEL SECURITY`, 12 políticas RLS granulares y sentencias DCL (`REVOKE ALL` + `GRANT` por tabla), con `downgrade()` simétrico completo en orden inverso (`payments` → `sale_items` → `sales`).
4. **Actualización de `docs/04-modelo-de-datos/erd.md`** (revisión `head` final al aplicar la migración) y verificación completa: `validate-db-migrations.js`, `uv run alembic upgrade head`, `uv run alembic check`, roundtrip (`alembic downgrade -1` / `downgrade base` → `upgrade head`), `ruff`, `mypy`, `pytest` y Mutation Testing.

## Open Questions

- Ninguna bloqueante. Quedan explícitas para confirmación del usuario antes de pasar a DB-TDD:
  1. `sale_items` en 3NF omite la columna derivada `subtotal` (se calcula como `quantity * unit_price` y el total reside en `sales.total_amount`).
  2. `payments.payment_method` restringe los valores del MVP a `('cash', 'card', 'transfer')` (alineado al reporte diario `us-04`).
  3. `fk_sale_items_product` aplica `ON DELETE RESTRICT` para proteger el histórico de ventas ante borrados accidentales de productos (complementando `is_active = false`).
