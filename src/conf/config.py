"""Налаштування застосунку.

Усі значення читаються з файла ``.env`` — у кодовій базі немає секретів
у відкритому вигляді.
"""

from pydantic import EmailStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Конфігурація застосунку, зчитана зі змінних оточення та ``.env``."""

    DB_URL: str

    # JWT
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_SECONDS: int = 3600
    JWT_REFRESH_EXPIRATION_SECONDS: int = 604800  # 7 днів
    PASSWORD_RESET_EXPIRATION_SECONDS: int = 3600

    # SMTP
    MAIL_USERNAME: EmailStr
    MAIL_PASSWORD: str
    MAIL_FROM: EmailStr
    MAIL_PORT: int = 465
    MAIL_SERVER: str = "smtp.meta.ua"
    MAIL_FROM_NAME: str = "Contacts API"
    MAIL_STARTTLS: bool = False
    MAIL_SSL_TLS: bool = True
    USE_CREDENTIALS: bool = True
    VALIDATE_CERTS: bool = True

    # Cloudinary
    CLD_NAME: str
    CLD_API_KEY: str
    CLD_API_SECRET: str

    # Redis (кеш поточного користувача)
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str | None = None
    REDIS_ENABLED: bool = True
    USER_CACHE_TTL: int = 900  # секунд

    # Ліміт запитів до /api/users/me
    USER_ME_RATE_LIMIT: str = "10/minute"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


config = Settings()
settings = config  # зручний аліас
