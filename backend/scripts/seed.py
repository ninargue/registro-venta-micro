"""
Seed del entorno de desarrollo local.

Pobla la base de datos con dos negocios de prueba, sus usuarios, catálogo de
productos y ventas de muestra. Es idempotente: se puede ejecutar varias veces
sin duplicar datos (ON CONFLICT DO NOTHING + UUIDs deterministas).

Uso:
    cd backend
    uv run python -m scripts.seed

Requisitos previos:
    - supabase start      (DB en 54422, Auth API en 54421)
    - make migrate        (migraciones aplicadas)
    - backend/.env con SUPABASE_SERVICE_ROLE_KEY y SUPABASE_URL configurados
      (obtener service-role key de: supabase status)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Credenciales de prueba               Contraseña
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Negocio A — Kiosco Don Carlos
  owner:   owner_a@example.com      Seed1234!
  cajero:  cashier_a@example.com    Seed1234!

Negocio B — Verdulería La Flor
  owner:   owner_b@example.com      Seed1234!
  cajero:  cashier_b@example.com    Seed1234!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from __future__ import annotations

import asyncio
import uuid
from decimal import Decimal

import asyncpg
import httpx

from app.core.config import get_settings

# ── Constantes ─────────────────────────────────────────────────────────────────

SEED_PASSWORD = "Seed1234!"

# Namespace determinista para generar UUIDs reproducibles entre ejecuciones.
_NS = uuid.UUID("00000000-0000-0000-0000-deed5eed0001")

BIZ_A_ID = uuid.uuid5(_NS, "negocio-a")
BIZ_B_ID = uuid.uuid5(_NS, "negocio-b")

# ── Datos de semilla ───────────────────────────────────────────────────────────

BUSINESSES: list[dict] = [
    {
        "id": BIZ_A_ID,
        "name": "Kiosco Don Carlos",
        "country": "AR",
        "timezone": "America/Argentina/Buenos_Aires",
    },
    {
        "id": BIZ_B_ID,
        "name": "Verdulería La Flor",
        "country": "AR",
        "timezone": "America/Argentina/Buenos_Aires",
    },
]

USERS: list[dict] = [
    {"email": "owner_a@example.com", "role": "owner", "biz_id": BIZ_A_ID},
    {"email": "cashier_a@example.com", "role": "cashier", "biz_id": BIZ_A_ID},
    {"email": "owner_b@example.com", "role": "owner", "biz_id": BIZ_B_ID},
    {"email": "cashier_b@example.com", "role": "cashier", "biz_id": BIZ_B_ID},
]

PRODUCTS: list[dict] = [
    # ── Negocio A: Kiosco ──
    {
        "biz_id": BIZ_A_ID,
        "code": "K001",
        "name": "Coca-Cola 500ml",
        "sale_price": Decimal("800"),
        "cost_price": Decimal("500"),
        "stock": Decimal("50"),
    },
    {
        "biz_id": BIZ_A_ID,
        "code": "K002",
        "name": "Agua Mineral 500ml",
        "sale_price": Decimal("400"),
        "cost_price": Decimal("200"),
        "stock": Decimal("100"),
    },
    {
        "biz_id": BIZ_A_ID,
        "code": "K003",
        "name": "Alfajor Triple",
        "sale_price": Decimal("650"),
        "cost_price": Decimal("350"),
        "stock": Decimal("80"),
    },
    {
        "biz_id": BIZ_A_ID,
        "code": "K004",
        "name": "Cigarrillos x20",
        "sale_price": Decimal("2200"),
        "cost_price": Decimal("1800"),
        "stock": Decimal("30"),
    },
    {
        "biz_id": BIZ_A_ID,
        "code": "K005",
        "name": "Chicle Topline",
        "sale_price": Decimal("150"),
        "cost_price": Decimal("80"),
        "stock": Decimal("200"),
    },
    # ── Negocio B: Verdulería ──
    {
        "biz_id": BIZ_B_ID,
        "code": "V001",
        "name": "Tomate kg",
        "sale_price": Decimal("1200"),
        "cost_price": Decimal("700"),
        "stock": Decimal("20"),
    },
    {
        "biz_id": BIZ_B_ID,
        "code": "V002",
        "name": "Lechuga",
        "sale_price": Decimal("800"),
        "cost_price": Decimal("400"),
        "stock": Decimal("15"),
    },
    {
        "biz_id": BIZ_B_ID,
        "code": "V003",
        "name": "Zanahoria kg",
        "sale_price": Decimal("900"),
        "cost_price": Decimal("500"),
        "stock": Decimal("25"),
    },
    {
        "biz_id": BIZ_B_ID,
        "code": "V004",
        "name": "Papa kg",
        "sale_price": Decimal("750"),
        "cost_price": Decimal("400"),
        "stock": Decimal("40"),
    },
    {
        "biz_id": BIZ_B_ID,
        "code": "V005",
        "name": "Cebolla kg",
        "sale_price": Decimal("600"),
        "cost_price": Decimal("350"),
        "stock": Decimal("30"),
    },
]

# ── Helpers ────────────────────────────────────────────────────────────────────


def _prod_id(biz_id: uuid.UUID, code: str) -> uuid.UUID:
    return uuid.uuid5(biz_id, f"product:{code}")


def _sale_id(biz_id: uuid.UUID, suffix: str) -> uuid.UUID:
    return uuid.uuid5(biz_id, f"sale:{suffix}")


def _client_id(biz_id: uuid.UUID, suffix: str) -> uuid.UUID:
    """
    client_id = clave de idempotencia generada por el cliente (patrón offline-first).
    Se usa como llave de deduplicación en la tabla sales.
    """
    return uuid.uuid5(biz_id, f"client:{suffix}")


def _asyncpg_dsn(url: str) -> str:
    """Convierte URL SQLAlchemy (postgresql+asyncpg://) a DSN puro para asyncpg."""
    return url.replace("postgresql+asyncpg://", "postgresql://")


# ── Supabase Auth ──────────────────────────────────────────────────────────────


async def _upsert_auth_user(
    client: httpx.AsyncClient,
    base_url: str,
    service_key: str,
    email: str,
) -> uuid.UUID:
    """
    Crea el usuario en Supabase Auth o recupera su UUID si ya existe.
    Usa el endpoint Admin API (requiere service_role key).
    """
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
    }

    r = await client.post(
        f"{base_url}/auth/v1/admin/users",
        headers=headers,
        json={"email": email, "password": SEED_PASSWORD, "email_confirm": True},
    )

    if r.status_code in (200, 201):
        return uuid.UUID(r.json()["id"])

    # 422 = el email ya existe en Supabase Auth → recuperar por listado
    if r.status_code == 422:
        r2 = await client.get(
            f"{base_url}/auth/v1/admin/users",
            headers=headers,
            params={"per_page": 200},
        )
        r2.raise_for_status()
        users_list = r2.json().get("users", [])
        match = next((u for u in users_list if u["email"] == email), None)
        if match:
            return uuid.UUID(match["id"])

    r.raise_for_status()
    raise RuntimeError(f"No se pudo crear/recuperar el usuario {email}: {r.text}")


# ── Seed principal ─────────────────────────────────────────────────────────────


async def seed() -> None:
    settings = get_settings()

    # Validar configuración mínima para el seed
    supabase_url = settings.supabase_url
    service_key = settings.supabase_service_role_key
    if not supabase_url or not service_key:
        raise RuntimeError(
            "\n✗ Faltan variables en backend/.env:\n"
            "  SUPABASE_URL           → obtenelo de: supabase status\n"
            "  SUPABASE_SERVICE_ROLE_KEY → obtenelo de: supabase status\n"
        )

    # URL de admin: postgres superuser, omite RLS (BYPASSRLS por defecto en superuser).
    # Se usa DATABASE_ADMIN_URL si está definido; si no, se deriva de DATABASE_URL.
    admin_dsn = _asyncpg_dsn(
        settings.database_admin_url
        or settings.database_url.replace(
            "app_runtime:app_runtime_dev_password",
            "postgres:postgres",
        )
    )

    # ── 1. Crear usuarios en Supabase Auth ─────────────────────────────────────
    print("\n→ Creando usuarios en Supabase Auth...")
    user_ids: dict[str, uuid.UUID] = {}

    async with httpx.AsyncClient(timeout=10.0) as http:
        for u in USERS:
            uid = await _upsert_auth_user(http, supabase_url, service_key, u["email"])
            user_ids[u["email"]] = uid
            print(f"  ✓ {u['email']}  ({uid})")

    # ── 2. Insertar datos de aplicación ────────────────────────────────────────
    # Conectamos como postgres superuser: tiene BYPASSRLS, no necesita SET LOCAL.
    print("\n→ Conectando a la base de datos como superuser...")
    conn: asyncpg.Connection = await asyncpg.connect(admin_dsn)

    try:
        # 2a. Negocios
        print("→ Sembrando negocios...")
        for biz in BUSINESSES:
            await conn.execute(
                """
                INSERT INTO businesses (id, name, country, timezone)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT DO NOTHING
                """,
                biz["id"],
                biz["name"],
                biz["country"],
                biz["timezone"],
            )
            print(f"  ✓ {biz['name']}  ({biz['id']})")

        # 2b. Membresías business_users
        print("→ Sembrando membresías...")
        for u in USERS:
            uid = user_ids[u["email"]]
            await conn.execute(
                """
                INSERT INTO business_users (business_id, user_id, role)
                VALUES ($1, $2, $3)
                ON CONFLICT DO NOTHING
                """,
                u["biz_id"],
                uid,
                u["role"],
            )
            print(f"  ✓ {u['email']}  → {u['role']}")

        # 2c. Productos
        print("→ Sembrando productos...")
        for p in PRODUCTS:
            pid = _prod_id(p["biz_id"], p["code"])
            await conn.execute(
                """
        INSERT INTO products (id, business_id, code, name, sale_price, cost_price, stock, is_active)
        VALUES ($1, $2, $3, $4, $5, $6, $7, true)
        ON CONFLICT DO NOTHING
        """,
                pid,
                p["biz_id"],
                p["code"],
                p["name"],
                p["sale_price"],
                p["cost_price"],
                p["stock"],
            )
        print(f"  ✓ {len(PRODUCTS)} productos")

        # 2d. Ventas de muestra (2 por negocio)
        print("→ Sembrando ventas de muestra...")
        total_sales = 0
        for biz in BUSINESSES:
            biz_products = [p for p in PRODUCTS if p["biz_id"] == biz["id"]]
            for i in range(2):
                sale_id = _sale_id(biz["id"], str(i))
                client_id = _client_id(biz["id"], str(i))
                prod = biz_products[i % len(biz_products)]
                prod_id = _prod_id(biz["id"], prod["code"])
                qty = Decimal("2")
                total = prod["sale_price"] * qty

                await conn.execute(
                    """
                    INSERT INTO sales (id, business_id, client_id, total_amount)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT DO NOTHING
                    """,
                    sale_id,
                    biz["id"],
                    client_id,
                    total,
                )

                item_id = uuid.uuid5(sale_id, "item-0")
                await conn.execute(
                    """
                    INSERT INTO sale_items (id, business_id, sale_id, product_id,
                                           quantity, unit_price, unit_cost)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT DO NOTHING
                    """,
                    item_id,
                    biz["id"],
                    sale_id,
                    prod_id,
                    qty,
                    prod["sale_price"],
                    prod["cost_price"],
                )

                payment_id = uuid.uuid5(sale_id, "payment-0")
                await conn.execute(
                    """
                    INSERT INTO payments (id, business_id, sale_id, payment_method, amount)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT DO NOTHING
                    """,
                    payment_id,
                    biz["id"],
                    sale_id,
                    "cash",
                    total,
                )
                total_sales += 1

        print(f"  ✓ {total_sales} ventas de muestra ({total_sales} items + {total_sales} pagos)")

    finally:
        await conn.close()

    # ── Resumen final ──────────────────────────────────────────────────────────
    print("""
✅ Seed completado. Credenciales de prueba:

   Negocio A — Kiosco Don Carlos
     owner:   owner_a@example.com   / Seed1234!
     cajero:  cashier_a@example.com / Seed1234!

   Negocio B — Verdulería La Flor
     owner:   owner_b@example.com   / Seed1234!
     cajero:  cashier_b@example.com / Seed1234!
""")


if __name__ == "__main__":
    asyncio.run(seed())
