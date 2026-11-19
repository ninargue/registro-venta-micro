# Design: Endpoints de ciclo de sesión (`issue-55-auth-session-lifecycle-backend`)

## Convenciones de infraestructura detectadas
- `backend_dir`: `backend/app`
- `tests_dir`: `backend/tests`
- `test_cmd`: `cd backend && uv run pytest`
- `lint_cmd`: `cd backend && uv run ruff check .`
- `typecheck_cmd`: `cd backend && uv run mypy app`
- `db_mode`: `with-db` (sin cambios de esquema en este ticket)

## Diseño Técnico
1. **Configuración (`app/core/config.py`):**
   - `refresh_cookie_name: str = "refresh_token"`
   - `refresh_token_expire_days: int = 7`
2. **Seguridad JWT (`app/core/security.py`):**
   - `create_access_token` incluye `"token_type": "access"`.
   - `decode_access_token` rechaza si `payload.get("token_type") == "refresh"`.
   - `create_refresh_token(user_id, email, settings)` firma JWT con `"token_type": "refresh"` y `exp = now + refresh_token_expire_days * 86400`.
   - `decode_refresh_token(token, settings)` exige `payload.get("token_type") == "refresh"` y retorna `CurrentUser(user_id, email)`.
   - `get_refresh_user(request, settings)` extrae `request.cookies.get(settings.refresh_cookie_name)` y valida con `decode_refresh_token` (`401` si falta o es inválido).
3. **Servicio (`app/modules/auth/service.py`):**
   - Helper `_build_session_payload(user_id, email, membership) -> tuple[LoginResponse, str, str]` reutilizado por `login`, `refresh` y `me` (para evitar duplicación).
   - `login(...) -> tuple[LoginResponse, str, str]` (devuelve `access_token` y `refresh_token`).
   - `onboard(...) -> tuple[BusinessResponse, str, str]` (devuelve `access_token` y `refresh_token`).
   - `get_me(current_user) -> LoginResponse`: consulta `get_user_membership(current_user.user_id)` y construye `LoginResponse`.
   - `refresh(refresh_user) -> tuple[LoginResponse, str, str]`: consulta `get_user_membership(refresh_user.user_id)` y emite nuevos `access_token` y `refresh_token`.
4. **Router (`app/modules/auth/router.py`):**
   - `_set_session_cookies(response, access_token, refresh_token, settings)`
   - `_clear_session_cookies(response, settings)`
   - `GET /api/v1/auth/me` -> `200 LoginResponse`
   - `POST /api/v1/auth/logout` -> `204 No Content`
   - `POST /api/v1/auth/refresh` -> `200 LoginResponse`
