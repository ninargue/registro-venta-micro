# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Estado actual

Entrega 1 — documentación técnica del MVP, **sin código todavía**. El repositorio contiene únicamente el README técnico, el log de prompts, el CHANGELOG y la configuración de GitHub (workflows, templates, CONTRIBUTING). El código se agrega en la Entrega 2.

## Comandos de desarrollo (previstos para cuando exista el código)

```bash
# Supabase local (Docker)
supabase start

# Backend
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
alembic upgrade head
python -m scripts.seed
uvicorn app.main:app --reload        # http://localhost:8000/docs

# Frontend
cd frontend
npm ci
npm run dev                          # http://localhost:5173

# Tests
cd backend && pytest                 # unitarios, integración y aislamiento multitenant
cd frontend && npm test              # Vitest
npx playwright test                  # E2E

# Un solo test de backend
pytest tests/path/to/test_file.py::test_name
```

## Arquitectura

**Patrón:** cliente-servidor API-first, monolito modular en el backend, PWA offline-first en el cliente.

- **Frontend:** React 18 + Vite + TypeScript + TanStack Query. PWA con Service Worker (Workbox) e IndexedDB (Dexie) para catálogo, caja abierta y **outbox** de ventas pendientes.
- **Backend:** FastAPI + SQLAlchemy 2 async + asyncpg. Capas `Router → Service → Repository`. Módulos de dominio: `auth`, `tenancy`, `catalog`, `sales`, `inventory`, `cash`, `reports`, `assistant`.
- **Base de datos:** PostgreSQL 17 vía Supabase (`sa-east-1`). Multitenant con `tenant_id NOT NULL` en toda tabla operativa y RLS forzada. Las migraciones son la única vía para cambiar el esquema (Alembic, nunca el panel de Supabase).
- **Auth:** Supabase Auth para credenciales; el backend emite su propia sesión (access JWT 15 min + refresh rotativo en cookies `HttpOnly; Secure; SameSite=Strict`). El navegador nunca habla con Supabase.
- **Despliegue:** Vercel sirve la PWA (CDN) y la API (función Python en `gru1`) bajo el mismo dominio. CI obligatorio antes de cualquier deploy; producción requiere aprobación manual.

### Invariantes de seguridad críticos

- El tenant siempre sale del token JWT, nunca del body ni de la URL.
- El backend fija `SET LOCAL app.tenant_id` en cada transacción; las políticas RLS lo usan.
- Recursos de otro tenant responden `404` (no revelar que existen).
- El asistente de IA nunca genera SQL: solo invoca reportes predefinidos que corren bajo RLS.

### Offline / idempotencia

- Las ventas y cajas reciben UUID generado en el cliente (llave de idempotencia).
- `POST /api/v1/sales` usa `INSERT … ON CONFLICT (id) DO NOTHING`; un reenvío del outbox devuelve `200` sin duplicar stock.
- Una venta que llega después del cierre de su caja se acepta con `synced_after_close = true` y recalcula el cierre.

## Convención de branches y commits

Formato de rama: `<tipo>/<descripcion-en-kebab-case>` (minúsculas, sin tildes, sin guiones bajos).  
Tipos válidos: `feature/`, `fix/`, `hotfix/`, `chore/`, `refactor/`, `docs/`, `test/`, `release/vX.Y.Z`.  
El workflow **Branch Policy** rechaza nombres inválidos: un PR con nombre incorrecto no puede mergearse.

Commits con [Conventional Commits](https://www.conventionalcommits.org/es/v1.0.0/): `<tipo>(<alcance>): <descripción imperativo, minúsculas>`.  
Alcances sugeridos: `auth`, `tenancy`, `catalogo`, `ventas`, `caja`, `inventario`, `reportes`, `ia`, `sync`, `db`.

PRs hacia `develop` → **Squash and merge** (el título del PR se convierte en el commit).  
PRs hacia `master` (`release/*`, `hotfix/*`) → **Create a merge commit**.

## Flujo GitFlow resumido

- Todo cambio parte de un issue y una rama desde `develop` actualizado.
- PR en borrador al primer commit; cambiar a "Ready for review" tras autorrevisión.
- La rama debe estar actualizada con su destino antes del merge (exigido por las protecciones de `develop` y `master`).
- Releases y hotfixes terminan con tag `vX.Y.Z` + release en GitHub con notas del changelog.
- El workflow **Backport PR** abre automáticamente el PR de backport a `develop`; hay que cerrarlo y reabrirlo para disparar el check obligatorio.
