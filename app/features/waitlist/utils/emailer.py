import smtplib
import logging
from email.mime.text import MIMEText
from app.platform import config
from app.platform.services.email import send_email

def send_thank_you_email(to_email: str, name: str):
    try:
        subject = "Thank you for joining the waitlist"
        body = f"Hi {name},\n\nThank you for joining the waitlist!"
        send_email(to_email, subject, body)
    except Exception as e:
        logging.error(f"Failed to send email: {e}")