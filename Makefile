# Atajos para desarrollo local. Requiere GNU Make (Linux/macOS: viene instalado;
# Windows: `choco install make` o usar Git Bash/WSL). Sin Make, los comandos
# equivalentes estan en el README (seccion 1.4).

.DEFAULT_GOAL := help
.PHONY: help install db-up db-down env-supabase setup migrate seed backend-dev frontend-dev \
        test test-backend test-backend-unit test-frontend test-e2e lint

help: ## Lista los comandos disponibles
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  make %-20s %s\n", $$1, $$2}'

# ---------------------------------------------------------------------------
# Regla de archivo: Make crea backend/.env desde .env.example solo si no existe.
# Al ser una regla de archivo (no PHONY), se ejecuta una única vez.
# ---------------------------------------------------------------------------
backend/.env:
	@cp backend/.env.example backend/.env
	@echo ""
	@echo "  [OK] backend/.env creado con valores por defecto para Supabase local."
	@echo "  -> Ejecuta 'make env-supabase' (con Supabase en ejecucion) para inyectar las claves reales."
	@echo ""

install: ## Instala hooks de git, dependencias del backend y del frontend
	npm install
	cd backend && uv sync
	cd frontend && npm ci
	@echo ""
	@echo "    Dependencias instaladas. Siguientes pasos:"
	@echo "    make setup    ->  inicia Supabase, inyecta claves, migra y seedea (una sola vez)"
	@echo "    make backend-dev + make frontend-dev  ->  inicia los servidores"
	@echo ""

db-up: ## Inicia Supabase local (Docker)
	@if ! docker info > /dev/null 2>&1; then \
		echo ""; \
		echo "  [ERROR] Docker Desktop no esta en ejecucion."; \
		echo "          Inicia Docker Desktop y vuelve a ejecutar: make db-up"; \
		echo ""; \
		exit 1; \
	fi
	supabase start

db-down: ## Detiene Supabase local
	supabase stop

env-supabase: backend/.env ## Inyecta claves de Supabase en backend/.env (requiere make db-up primero)
	@STATUS=$$(supabase status 2>&1); \
	if ! echo "$$STATUS" | grep -q "Project URL"; then \
		echo ""; \
		echo "  [ERROR] Supabase no esta en ejecucion."; \
		echo "          Verifica que Docker Desktop este iniciado y ejecuta: make db-up"; \
		echo ""; \
		exit 1; \
	fi; \
	API=$$(echo "$$STATUS" | grep "Project URL" | grep -oE 'https?://[0-9.:]+'); \
	ANON=$$(echo "$$STATUS" | grep -oE 'sb_publishable_[A-Za-z0-9_]+'); \
	SRK=$$(echo "$$STATUS" | grep -oE 'sb_secret_[A-Za-z0-9_-]+'); \
	sed -i "s|SUPABASE_URL=.*|SUPABASE_URL=$$API|" backend/.env; \
	sed -i "s|SUPABASE_ANON_KEY=.*|SUPABASE_ANON_KEY=$$ANON|" backend/.env; \
	sed -i "s|SUPABASE_SERVICE_ROLE_KEY=.*|SUPABASE_SERVICE_ROLE_KEY=$$SRK|" backend/.env; \
	echo ""; \
	echo "  [OK] backend/.env actualizado con claves de Supabase local."; \
	echo ""

setup: ## Setup completo: db-up -> claves -> migrate -> seed
	$(MAKE) db-up
	$(MAKE) env-supabase
	$(MAKE) migrate
	$(MAKE) seed
	@echo ""
	@echo "  [OK] Entorno listo. Inicia los servidores con:"
	@echo "    make backend-dev   ->  API en http://localhost:8000/docs"
	@echo "    make frontend-dev  ->  PWA en http://localhost:5174"
	@echo ""

migrate: backend/.env ## Aplica las migraciones de Alembic
	cd backend && uv run alembic upgrade head

seed: backend/.env ## Carga datos ficticios (negocios, usuarios, productos y ventas)
	cd backend && uv run python -m scripts.seed

backend-dev: ## API en http://localhost:8000/docs (requiere make setup o make db-up+migrate)
	cd backend && uv run uvicorn app.main:app --reload

frontend-dev: ## PWA en http://localhost:5174
	cd frontend && npm run dev

test-backend-unit: ## Tests unitarios del backend (no requieren base de datos)
	cd backend && uv run pytest tests/unit

test-backend: ## Todos los tests del backend (requieren db-up y migrate)
	cd backend && uv run pytest

test-frontend: ## Tests unitarios y de componentes del frontend (Vitest)
	cd frontend && npm test

test-e2e: ## Tests E2E (Playwright; instala Chromium si falta)
	cd frontend && npm run test:e2e

test: test-backend test-frontend test-e2e ## Ejecuta todos los tests

lint: ## Lint y tipos de backend y frontend
	cd backend && uv run ruff check . && uv run mypy app
	cd frontend && npm run lint && npm run typecheck && npm run format:check
