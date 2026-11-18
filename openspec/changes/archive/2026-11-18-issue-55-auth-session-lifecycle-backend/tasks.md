# Tasks: issue-55-auth-session-lifecycle-backend

- [x] 1.1 [Backend-TDD ROJO] Agregar tests de integración en `backend/tests/integration/test_auth_onboarding.py` para `GET /api/v1/auth/me` (200 con/sin comercio, 401 sin cookie o token inválido), `POST /api/v1/auth/logout` (204 limpiando cookies), `POST /api/v1/auth/refresh` (200 con refresh válido, 401 sin cookie/expirado/access_token usado como refresh) y emisión de `refresh_token` en `/login` y `/onboarding`; verificar fallo en ROJO.
- [x] 2.1 Actualizar `backend/app/core/config.py` y `backend/app/core/security.py` con soporte de `refresh_token` y `token_type`.
- [x] 2.2 Actualizar `backend/app/modules/auth/service.py` y `backend/app/modules/auth/router.py` implementando `/me`, `/logout`, `/refresh` y cookies duales en `/login` y `/onboarding`.
- [x] 3.1 Ejecutar Gates 3 y 4 (`ruff check .`, `mypy app`, `pytest`) y verificar todo en VERDE.
