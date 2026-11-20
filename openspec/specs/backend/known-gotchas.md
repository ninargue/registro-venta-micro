# Known Gotchas — backend

Reglas breves promovidas tras fallos reales del repositorio. Leer solo esta capa en `opsx:explore`.

- En FastAPI + SQLAlchemy asyncpg con pytest-asyncio (scope function) y Vercel/Supabase Pooler, usar poolclass=NullPool en create_async_engine para evitar RuntimeError: Event loop is closed.
