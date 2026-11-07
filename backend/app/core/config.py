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


@lru_cache
def get_settings() -> Settings:
    """Devuelve la configuración cacheada; se evalúa al primer uso, no al importar."""
    return Settings()
