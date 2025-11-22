from pydantic_settings import BaseSettings
from typing import Literal, Optional
from pathlib import Path


class Settings(BaseSettings):
    # ── App ─────────────────────────────────────
    APP_NAME: str = "SiteMate AI"
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"
    DEBUG: bool = True

    # ── Database ────────────────────────────────
    DATABASE_URL: str = 'sqlite+aiosqlite:///./site_audit.db'
    
    # ── Email Configuration ─────────────────────
    MAIL_MAILER: str = "smtp"
    MAIL_HOST: str = "smtp.gmail.com"
    MAIL_PORT: int = 587
    MAIL_USERNAME: str ='your-email-id'
    MAIL_PASSWORD: str = 'your-password'
    MAIL_ENCRYPTION: str = "tls"
    MAIL_FROM_ADDRESS: str = 'example@localhost'
    MAIL_FROM_NAME: str = 'SiteMate AI'
    GOOGLE_CLIENT_ID: str = 'dummy-value'
    GOOGLE_CLIENT_ID_ANDROID: Optional[str] = None

    # ── JWT / Auth ──────────────────────────────
    JWT_SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    class Config:
        env_file = str(Path(__file__).parent.parent.parent / ".env")
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"

settings = Settings()