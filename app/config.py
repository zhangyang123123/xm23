from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "API Audit Platform"
    APP_ENV: str = "dev"
    DEBUG: bool = True

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/api_audit"

    ADMIN_TOKEN: str = "admin-token-change-me"

    AUDIT_BODY_MAX_SIZE: int = 1024 * 32


settings = Settings()
