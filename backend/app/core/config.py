from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://localhost/registro_venta"
    secret_key: str = "dev-secret-key"
    environment: str = "development"


settings = Settings()
