from pathlib import Path
import os
from dotenv import load_dotenv

from pydantic_settings import BaseSettings
from typing import Literal, Optional
from typing import Literal, Optional

from pydantic_settings import BaseSettings

load_dotenv()


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

    # ── Apple OAuth Configuration ───────────────────────
    APPLE_CLIENT_ID: Optional[str] = os.getenv("APPLE_CLIENT_ID", None)
    APPLE_TEAM_ID: Optional[str] = os.getenv("APPLE_TEAM_ID", None)
    APPLE_KEY_ID: Optional[str] = os.getenv("APPLE_KEY_ID", None)
    APPLE_PRIVATE_KEY_PATH: Optional[str] = os.getenv("APPLE_PRIVATE_KEY_PATH", None)
    APPLE_REDIRECT_URI: Optional[str] = os.getenv("APPLE_REDIRECT_URI", None)


    class Config:
        env_file = str(Path(__file__).parent.parent.parent / ".env")
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


settings = Settings()
