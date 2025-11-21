from typing import Literal, List
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── App ─────────────────────────────────────
    APP_NAME: str = "SiteMate AI"
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"
    DEBUG: bool = True

    # ── Database ────────────────────────────────
    DATABASE_URL: str

    # ── Redis Configuration ─────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Rate Limits ─────────────────────────────
    WAITLIST_REGISTER_LIMIT: int = 5
    WAITLIST_STATS_LIMIT: int = 10
    FORCE_IN_MEMORY_RATE_LIMITER: bool = False
    WHITELIST_IPS: List[str] = []

    @property
    def RATE_LIMITS(self) -> dict[str, int]:
        return {
            "/waitlist": self.WAITLIST_REGISTER_LIMIT,
            "/waitlist/stats": self.WAITLIST_STATS_LIMIT,
        }

    # ── Email Configuration ─────────────────────
    MAIL_MAILER: str
    MAIL_HOST: str
    MAIL_PORT: int = 587
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_ENCRYPTION: str
    MAIL_FROM_ADDRESS: str
    MAIL_FROM_NAME: str

    # ── JWT / Auth ──────────────────────────────
    JWT_SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24h
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    class Config:
        # Load .env from project root (since config.py is in app/platform/)
        env_file = Path(__file__).parent.parent.parent / ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


# Instantiate global settings
settings = Settings()