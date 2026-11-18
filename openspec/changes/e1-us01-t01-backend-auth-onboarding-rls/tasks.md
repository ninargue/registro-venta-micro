## 1. Dependencias, Configuración y Esquemas Pydantic (consumiendo `models.py` inmutable)

- [ ] 1.1 Agregar dependencia `tzdata` en `backend/pyproject.toml` mediante `cd backend && uv add tzdata` para soporte multiplataforma de `zoneinfo.ZoneInfo`
- [ ] 1.2 Extender `Settings` en `backend/app/core/config.py` con variables tipadas de Supabase Auth (`supabase_url`, `supabase_anon_key`), JWT/cookies (`jwt_secret_key`, `jwt_algorithm`, `access_token_expire_minutes`, `cookie_name`, `cookie_secure`) y `db_pool_statement_cache_size`, manteniendo compatibilidad cuando solo `database_url` esté configurado (sin secretos hardcodeados)
- [ ] 1.3 Implementar DTOs y validadores en `backend/app/modules/auth/schemas.py` (`LoginRequest`, `UserPayload`, `BusinessSummary`, `LoginResponse`, `OnboardingRequest`, `BusinessResponse`, `ErrorResponse`) con catálogo `COUNTRY_TIMEZONES` y validación IANA vía `zoneinfo.ZoneInfo` (`<= 50` caracteres) para zonas explícitas y resueltas por país

## 2. Sesión Transaccional RLS y Repositorio

- [ ] 2.1 Implementar engine async (`statement_cache_size=0` configurable) y dependencias transaccionales en `backend/app/core/db.py` ejecutando `SET LOCAL ROLE app_api`, `app.current_user_id` y `app.current_business_id` (`get_tenant_db`) mediante `set_config(..., ..., true)`
- [ ] 2.2 Implementar firma/validación de JWT (`PyJWT`), lectura desde cookie `HttpOnly` y dependencias de autenticación (`get_current_user`, `get_current_tenant`) en `backend/app/core/security.py` (`401` sin sesión válida, `403` si `business_id` es `null`)
- [ ] 2.3 Implementar `AuthRepository` en `backend/app/modules/auth/repository.py` consumiendo los modelos inmutables `Business` y `BusinessUser` de `backend/app/modules/auth/models.py`: lectura de membresía en dos pasos en login (`app.current_user_id` → `business_users`; luego `app.current_business_id` → `businesses`) y alta atómica en onboarding (`business_id = uuid4()` en Python, `app.current_user_id` + `app.current_business_id` previos a `INSERT INTO businesses ... RETURNING` + `INSERT INTO business_users` con rol `owner`)

## 3. Capa de Servicio

- [ ] 3.1 Implementar `AuthService` en `backend/app/modules/auth/service.py` para autenticar contra Supabase Auth vía `httpx.AsyncClient` (con `supabase_anon_key`, prohibido `service_role`), resolver membresía/comercio y emitir JWT de sesión (`requires_onboarding: true` cuando no hay negocio)
- [ ] 3.2 Implementar flujo de onboarding en `backend/app/modules/auth/service.py` rechazando usuarios con comercio existente, ejecutando alta transaccional, capturando `IntegrityError` (`23505` en `uq_business_users_user_id`) con rollback completo hacia `409 Conflict` ante concurrencia/reintentos y emitiendo JWT actualizado con el nuevo `business_id` y rol `owner`

## 4. Routers FastAPI y Registro en App

- [ ] 4.1 Implementar endpoints `POST /api/v1/auth/login` y `POST /api/v1/auth/onboarding` en `backend/app/modules/auth/router.py` emitiendo cookies `HttpOnly; SameSite=Strict` (`Secure` configurable) y respuestas estructuradas de error (`401`, `403`, `409`, `422`)
- [ ] 4.2 Registrar `auth_router` en `backend/app/main.py` bajo prefijo `/api/v1` (sin modificar `backend/migrations/` ni `backend/app/modules/auth/models.py`)

## 5. Pruebas de Dominio y Validación de Calidad

- [ ] 5.1 Implementar pruebas unitarias y de integración por dominio (`backend/tests/unit/test_auth_schemas.py`, `backend/tests/integration/test_auth_onboarding.py`) cubriendo cada escenario `spec.md`: login con negocio (`200`), login con `requires_onboarding` (`200`), credenciales inválidas (`401`), onboarding por país (`201`), onboarding con `timezone` explícito válido (`201`), rechazo de `timezone` IANA inválido vía `ZoneInfo` (`422`), país/nombre inválido (`422`), no autenticado (`401`), duplicado (`409`) y concurrencia sin huérfanos (`409`)
- [ ] 5.2 Implementar pruebas de aislamiento RLS bajo rol `app_api` verificando contexto de login (`app.current_user_id` sin deadlock), contexto de tenant (`app.current_business_id`), bloqueo sin contexto (`401`/`403`) y aislamiento cruzado entre negocios
- [ ] 5.3 Ejecutar validación determinista y calidad (`cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy app && uv run pytest`) garantizando 0 modificaciones en `backend/migrations/` y `models.py`
