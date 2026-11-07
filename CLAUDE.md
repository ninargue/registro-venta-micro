# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Estado actual

Entrega 2 — scaffold en marcha. Ya existen:

- **Backend:** FastAPI con `GET /api/v1/health`; config con `pydantic-settings`; tooling uv + ruff + mypy + pytest.
- **Base de datos:** Supabase local (Docker) y Alembic inicializado con la migración baseline (vacía).
- **Frontend:** React + Vite con una ruta (`/`), Vitest y un smoke test E2E con Playwright.
- **Hooks de git:** husky + lint-staged (pre-commit y pre-push).
- **CI:** workflows `ci-backend.yml` y `ci-frontend.yml` en `.github/workflows/`.

**Plan:** lo siguiente son los módulos de dominio a partir de los tickets del README; el plugin PWA (Workbox) se configura junto con la funcionalidad offline.

## Comandos de desarrollo

Node 26 vía [fnm](https://github.com/Schniz/fnm) (lee `.nvmrc`).

```bash
# Hooks de git (una vez, en la raíz del repo): instala husky + lint-staged
npm install

# Supabase local (Docker)
supabase start                       # stack completo
# supabase db start                  # solo Postgres (p. ej. migraciones/tests)

# Backend
cd backend
uv sync                              # instala dependencias (prod + dev) en .venv
uv run alembic upgrade head
uv run uvicorn app.main:app --reload # http://localhost:8000/docs

# Frontend
cd frontend
npm ci
npm run dev                          # http://localhost:5174

# Tests que existen hoy
cd backend && uv run pytest          # unitarios (tests/unit/test_health.py)
cd frontend && npm test              # Vitest (src/app/router.test.tsx)
cd frontend && npm run test:e2e      # Playwright E2E (tests/e2e/smoke.spec.ts)

# Un solo test de backend
uv run pytest tests/path/to/test_file.py::test_name
```

## Reglas para el agente

- Hacer cada commit mediante el skill `commit`.
- No hacer `git push` hasta que el usuario lo confirme explícitamente, en cada ocasión. Excepción: el push inicial que crea la rama en el remoto al iniciarla (skill `lifecycle-dev`).
- No desactivar reglas de lint ni de tipos para que pase un check.
- Agregar dependencias con `uv add` (backend) o `npm install` (frontend/raíz), nunca editando los manifiestos a mano.
- Antes de afirmar qué soporta una plataforma (Vercel, Supabase, GitHub) o qué versión de una action existe, consultar la fuente y citarla.
- Al commitear, agregar solo los archivos del cambio (nunca `git add .` ni `-A`).

## Arquitectura

**Patrón:** cliente-servidor API-first, monolito modular en el backend, PWA offline-first en el cliente.

- **Frontend:** React 19 + Vite + TypeScript 6 + TanStack Query + React Router 8. PWA con Service Worker (Workbox) e IndexedDB (Dexie) para catálogo, caja abierta y **outbox** de ventas pendientes.
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

## Reglas de proceso
- Antes de iniciar el desarrollo de un issue, preparar rama, worktree, workspace de acuerdo al skill `lifecycle-dev`.
- Al cerrar la tarea: usar la skill `/commit`, luego `gh pr create` con una descripción completa de los cambios en el cuerpo del PR.
- Después de abrir el PR: usar el subagente `adversarial-reviewer` sobre él, antes de darlo por terminado.
- No repitas ese resumen en el chat: la sesión se va a perder, el PR no. Responde solo con la URL del PR.