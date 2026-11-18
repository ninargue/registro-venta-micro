from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración de la aplicación, leída del entorno (sin valores por defecto secretos)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Base de datos (rol app_api por el pooler de Supabase).
    database_url: str
    db_pool_statement_cache_size: int = 0

    # Supabase Auth (prohibido usar service_role en flujos de usuario).
    supabase_url: str | None = None
    supabase_anon_key: str | None = None

    # Sesión JWT y cookies HttpOnly.
    jwt_secret_key: str | None = None
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    cookie_name: str = "access_token"
    cookie_secure: bool = True


@lru_cache
def get_settings() -> Settings:
    """Devuelve la configuración cacheada; se evalúa al primer uso, no al importar."""
    return Settings()
