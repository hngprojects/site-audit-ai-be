import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USERNAME = os.getenv("EMAIL_USERNAME")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
FROM_EMAIL = os.getenv("FROM_EMAIL")
FROM_NAME = os.getenv("FROM_NAME", "SiteMate")