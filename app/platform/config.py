import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    REDIS_URL: str = "redis://localhost:6379"
     # Rate limiting configs
    FORCE_IN_MEMORY_RATE_LIMITER: bool = False
    # Rate limits
    WAITLIST_REGISTER_LIMIT: int = 5     # example: 5 requests/min
    WAITLIST_STATS_LIMIT: int = 10       # example: 10 requests/min

    # Optional: whitelisted IPs
    WHITELIST_IPS: list[str] = []

    @property
    def RATE_LIMITS(self):
        return {
            "waitlist": self.WAITLIST_REGISTER_LIMIT,
            "stats": self.WAITLIST_STATS_LIMIT,
        }
   

settings = Settings()

# Backward compatibility (middleware currently expects these)
REDIS_URL = settings.REDIS_URL
RATE_LIMITS = settings.RATE_LIMITS
WHITELIST_IPS = settings.WHITELIST_IPS

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
MAIL_MAILER = os.getenv("MAIL_MAILER")
MAIL_HOST = os.getenv("MAIL_HOST")
MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
MAIL_USERNAME = os.getenv("MAIL_USERNAME")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
MAIL_ENCRYPTION = os.getenv("MAIL_ENCRYPTION")
MAIL_FROM_ADDRESS = os.getenv("MAIL_FROM_ADDRESS")
MAIL_FROM_NAME = os.getenv("MAIL_FROM_NAME")

# Rate limiting config
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

RATE_LIMITS = {
    "waitlist": int(os.getenv("WAITLIST_RATE_LIMIT", 5)),  # 5 req/min
    "stats": int(os.getenv("STATS_RATE_LIMIT", 10)),        # 10 req/min
}

WHITELIST_IPS = os.getenv("WHITELIST_IPS", "").split(",")
