# Tasks: issue-54-hardening-auth-rls-backend

- [x] 1.1 [Backend-TDD ROJO] Agregar tests unitarios y de integración en `backend/tests/unit/test_auth_schemas.py` y `backend/tests/integration/test_auth_onboarding.py` para `429`/`5xx`/timeouts de Supabase Auth, rate limit en `/login`, formato `ErrorResponse` en `401`/`403`/`422`, byte `\x00`, `max_length`, validación de `JWT_SECRET_KEY < 32` bytes / `COOKIE_SECURE=false` en producción, `decode_access_token` estricto y limpieza de GUC residual; verificar fallo en ROJO.
- [x] 2.1 Actualizar `backend/app/core/config.py`, `backend/app/core/security.py`, `backend/app/core/db.py` y crear `backend/app/core/rate_limit.py`.
- [x] 2.2 Actualizar `backend/app/main.py` (lifespan con `httpx.AsyncClient` compartido y exception handlers unificados).
- [x] 2.3 Actualizar `backend/app/modules/auth/schemas.py`, `backend/app/modules/auth/repository.py`, `backend/app/modules/auth/service.py` y `backend/app/modules/auth/router.py`.
- [x] 2.4 Actualizar `backend/.env.example` documentando `app_runtime`, `COOKIE_SECURE` y variables de entorno.
- [x] 3.1 Ejecutar Gates 3 y 4 (`ruff check .`, `mypy app`, `pytest`) y verificar todo en VERDE.
