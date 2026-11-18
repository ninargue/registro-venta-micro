from functools import lru_cache
from typing import Literal, Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración de la aplicación, leída del entorno (sin valores por defecto secretos)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["development", "test", "staging", "production"] = "development"

    # Base de datos (rol app_runtime con NOBYPASSRLS en runtime).
    database_url: str
    db_pool_statement_cache_size: int = 0

    # Supabase Auth (prohibido usar service_role en flujos de usuario).
    supabase_url: str | None = None
    supabase_anon_key: str | None = None

    # Sesión JWT y cookies HttpOnly.
    jwt_secret_key: str | None = None
    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
    access_token_expire_minutes: int = 15
    cookie_name: str = "access_token"
    cookie_secure: bool = True

    # Rate limiting para /api/v1/auth/login.
    login_rate_limit_ip_max: int = 20
    login_rate_limit_email_max: int = 10
    login_rate_limit_window_seconds: int = 60

    @model_validator(mode="after")
    def validate_security_constraints(self) -> Self:
        """Valida longitud mínima de JWT_SECRET_KEY y guardrail de cookie segura en producción."""
        if self.jwt_secret_key is not None and len(self.jwt_secret_key.encode("utf-8")) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 bytes")
        if self.app_env == "production" and not self.cookie_secure:
            raise ValueError("COOKIE_SECURE must be True in production")
        return self


def validate_runtime_settings(settings: Settings) -> None:
    """Valida al arranque que los secretos obligatorios estén configurados en staging/producción."""
    if settings.app_env in ("staging", "production"):
        missing = [
            name
            for name, val in (
                ("JWT_SECRET_KEY", settings.jwt_secret_key),
                ("SUPABASE_URL", settings.supabase_url),
                ("SUPABASE_ANON_KEY", settings.supabase_anon_key),
            )
            if not val
        ]
        if missing:
            raise RuntimeError(f"Missing required runtime settings: {', '.join(missing)}")


@lru_cache
def get_settings() -> Settings:
    """Devuelve la configuración cacheada; se evalúa al primer uso, no al importar."""
    return Settings()
