import os
from dotenv import load_dotenv

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


SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")


FRONTEND_URL = os.getenv("FRONTEND_URL", "https://myfrontend.com")