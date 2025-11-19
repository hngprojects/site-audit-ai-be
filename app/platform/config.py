# app/platform/config.py

import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    # Redis Configuration
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Rate limits – configurable through env
    WAITLIST_REGISTER_LIMIT: int = int(os.getenv("WAITLIST_RATE_LIMIT", 5))
    WAITLIST_STATS_LIMIT: int = int(os.getenv("STATS_RATE_LIMIT", 10))

    # Allow using in-memory limiter for testing
    FORCE_IN_MEMORY_RATE_LIMITER: bool = False

    # Whitelisted IPs
    WHITELIST_IPS: list[str] = os.getenv("WHITELIST_IPS", "").split(",")

    @property
    def RATE_LIMITS(self):
        return {
            "/waitlist": self.WAITLIST_REGISTER_LIMIT,
            "/waitlist/stats": self.WAITLIST_STATS_LIMIT,
        }


# Instantiate global settings
settings = Settings()


# ======================================================
#   EXISTING PROJECT SETTINGS (kept from staging branch)
# ======================================================

# Database
DATABASE_URL = os.getenv("DATABASE_URL")

# Email Configuration
MAIL_MAILER = os.getenv("MAIL_MAILER")
MAIL_HOST = os.getenv("MAIL_HOST")
MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
MAIL_USERNAME = os.getenv("MAIL_USERNAME")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
MAIL_ENCRYPTION = os.getenv("MAIL_ENCRYPTION")
MAIL_FROM_ADDRESS = os.getenv("MAIL_FROM_ADDRESS")
MAIL_FROM_NAME = os.getenv("MAIL_FROM_NAME")

# JWT Configuration
JWT_SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY", "your-secret-key-change-this-in-production"
)
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440")  # 24h
)
ALGORITHM = "HS256"
