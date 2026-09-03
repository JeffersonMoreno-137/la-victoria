from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    # App
    PROJECT_NAME: str = "La Victoria Foundation - Legal Assistant & Booking API"
    ENVIRONMENT: str = "development"
    TIMEZONE: str = "America/New_York"
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000

    # AI (OpenAI)
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-5.6-luna"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres_password_local@localhost:5432/lavictoriadb"
    DATABASE_URL_SYNC: str = "postgresql://postgres:postgres_password_local@localhost:5432/lavictoriadb"

    # Security
    ADMIN_PASSWORD: str = "LaVictoriaAdmin2026!"
    SESSION_SECRET: str = "la_victoria_super_secret_session_key_2026_secure!"

    model_config = SettingsConfigDict(
        env_file="../../.env",
        extra="ignore"
    )

@lru_cache()
def get_settings() -> Settings:
    return Settings()
