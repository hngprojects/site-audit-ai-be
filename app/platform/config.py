from pathlib import Path
from typing import Literal, Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── App ─────────────────────────────────────
    APP_NAME: str = "SiteMate AI"
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"
    DEBUG: bool = True

    # ── Database ────────────────────────────────
    DATABASE_URL: str

    CELERY_BROKER_URL: str = "amqp://guest:guest@localhost:5672//"

    # Using Redis backend for results (supports chords and avoids database complexity)
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"  
    
    CELERY_TASK_SERIALIZER: str = "json"
    CELERY_RESULT_SERIALIZER: str = "json"
    CELERY_ACCEPT_CONTENT: str = "json"
    CELERY_TASK_TRACK_STARTED: bool = True
    CELERY_TASK_TIME_LIMIT: int = 3600  # 1 hour max per task

    # ── Email Configuration ─────────────────────
    MAIL_MAILER: str = "smtp"
    MAIL_HOST: str = "smtp.gmail.com"
    MAIL_PORT: int = 587
    MAIL_USERNAME: str = "your-email-id"
    MAIL_PASSWORD: str = "your-password"
    MAIL_ENCRYPTION: str = "tls"
    MAIL_FROM_ADDRESS: str = "example@localhost"
    MAIL_FROM_NAME: str = "SiteMate AI"
    MAIL_ADMIN_EMAIL:str = "example@localhost"

    EMAIL_RELAY_URL: str = ""
    EMAIL_RELAY_API_KEY: str = ""
    EMAIL_RELAY_TIMEOUT: int = 30

    GOOGLE_CLIENT_ID: str = "dummy-value"
    GOOGLE_CLIENT_ID_ANDROID: Optional[str] = None

    GLM_API_URL: Optional[str] = None
    GLM_API_KEY: Optional[str] = None

    GOOGLE_GEMINI_API_KEY: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None

    # ── JWT / Auth ──────────────────────────────
    JWT_SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    LANDING_PAGE_URL: str = "https://sitelytics.com"

    class Config:
        env_file = str(Path(__file__).parent.parent.parent / ".env")
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


settings = Settings()
