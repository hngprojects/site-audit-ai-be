# app/platform/config.py
import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Rate limits – can be changed easily in envs
    WAITLIST_REGISTER_LIMIT: int = int(os.getenv("WAITLIST_RATE_LIMIT", 5))
    WAITLIST_STATS_LIMIT: int = int(os.getenv("STATS_RATE_LIMIT", 10))

    # For testing without Redis
    FORCE_IN_MEMORY_RATE_LIMITER: bool = False

    WHITELIST_IPS: list[str] = os.getenv("WHITELIST_IPS", "").split(",")

    @property
    def RATE_LIMITS(self):
        return {
            "/waitlist": self.WAITLIST_REGISTER_LIMIT,
            "/waitlist/stats": self.WAITLIST_STATS_LIMIT,
        }


settings = Settings()
