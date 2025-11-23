import smtplib
import ssl
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Environment, FileSystemLoader
from app.platform.config import settings
from app.platform.logger import get_logger

# Initialize Logger
logger = get_logger("email_service")

current_dir = os.path.dirname(os.path.abspath(__file__))
template_dir = os.path.join(current_dir, "../../features/auth/template")

if not os.path.exists(template_dir):
    template_dir = os.path.join(os.getcwd(), "app/features/auth/template")

env = Environment(loader=FileSystemLoader(template_dir))


def send_email(to_email: str, subject: str, body: str):
    """Base function to send email via SMTP"""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.MAIL_FROM_ADDRESS
    msg["To"] = to_email

    msg.attach(MIMEText(body, 'html'))

    try:
        port = settings.MAIL_PORT
        
        logger.info(f" Connecting to {settings.MAIL_HOST}:{port}...")
        if port == 465:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(settings.MAIL_HOST, port, context=context) as server:
                server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
                server.sendmail(settings.MAIL_FROM_ADDRESS, to_email, msg.as_string())
        else:
            with smtplib.SMTP(settings.MAIL_HOST, port) as server:
                server.ehlo() 
                
                if str(settings.MAIL_ENCRYPTION).upper() in ["TLS", "TRUE"]:
                    server.starttls()
                    server.ehlo() 
                
                server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
                server.sendmail(settings.MAIL_FROM_ADDRESS, to_email, msg.as_string())

        logger.info(f"Email successfully sent to {to_email}")

    except Exception as e:
        logger.error(f"CRITICAL EMAIL ERROR: {str(e)}")