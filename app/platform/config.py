import os
from typing import Optional

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

load_dotenv()

# TODO: move all constants to Settings class
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
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-this-in-production")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 hours
ALGORITHM = "HS256"


class Settings(BaseSettings):
    """
    Application settings.

    Behavior:
        - If no value is passed for a field, the value is automatically loaded
          from the environment variables.
        - All default values are validated automatically by Pydantic.
        - Validation can be disabled if needed.

    Disabling Validation:
        - At the model level, set:
              model_config = {"validate_default": False}
        - At the field level, use:
              Field(validate_default=False)

    see:
        https://docs.pydantic.dev/latest/concepts/pydantic_settings/#usage
    """

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Google OAuth Settings
    GOOGLE_CLIENT_ID: str = Field(default="")
    GOOGLE_CLIENT_ID_ANDROID: Optional[str] = Field(default=None)

    class Config:
        env_file = ".env"
        case_sensitive = True
        # this is needed because all other constants in this file are treadted as extra which causes error
        extra = "ignore"


settings = Settings()  # pyright: ignore[reportCallIssue]
