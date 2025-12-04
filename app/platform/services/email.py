import os
import smtplib
import ssl
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

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
    """
    Send email via HTTP relay service
    Falls back to direct SMTP if relay is not configured.
    """
    if settings.EMAIL_RELAY_URL and settings.EMAIL_RELAY_API_KEY:
        try:
            send_email_via_relay(to_email, subject, body)
            return
        except Exception as e:
            logger.error(f"Email relay failed: {str(e)}")
            logger.info("Attempting direct SMTP as fallback...")
            try:
                send_email_direct_smtp(to_email, subject, body)
            except Exception as smtp_e:
                logger.error(f"SMTP fallback also failed: {str(smtp_e)}")
                raise smtp_e
    else:
        logger.warning("Email relay not configured, attempting direct SMTP")
        send_email_direct_smtp(to_email, subject, body)


def send_email_via_relay(to_email: str, subject: str, body: str):
    """Send email via HTTP relay service"""
    payload = {
        "to_email": to_email,
        "subject": subject,
        "body": body,
        "from_address": settings.MAIL_FROM_ADDRESS
    }
    
    headers = {
        "X-API-Key": settings.EMAIL_RELAY_API_KEY,
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(
            settings.EMAIL_RELAY_URL,
            json=payload,
            headers=headers,
            timeout=settings.EMAIL_RELAY_TIMEOUT
        )
        
        response.raise_for_status()
        
        result = response.json()
        logger.info(f"Email sent via relay to {to_email}: {result.get('message')}")
        
    except requests.exceptions.Timeout:
        logger.error(f"Email relay timeout for {to_email}")
        raise Exception("Email relay service timeout")
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Email relay request failed: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Response status: {e.response.status_code}")
            logger.error(f"Response body: {e.response.text}")
        raise Exception(f"Email relay service error: {str(e)}")
    
    except Exception as e:
        logger.error(f"Unexpected error sending email via relay: {str(e)}")
        raise

def send_email_direct_smtp(to_email: str, subject: str, body: str):
    """Base function to send email via SMTP"""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.MAIL_FROM_ADDRESS
    msg["To"] = to_email

    msg.attach(MIMEText(body, "html"))

    try:
        port = settings.MAIL_PORT
        
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


    except Exception as e:
        logger.error(f"CRITICAL EMAIL ERROR: {str(e)}")
