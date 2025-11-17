import smtplib
import logging
from email.mime.text import MIMEText
from app.platform import config

def send_thank_you_email(to_email: str, name: str):
    try:
        msg = MIMEText(f"Hi {name},\n\nThank you for joining the waitlist!")
        msg["Subject"] = "Thank you for joining the waitlist"
        msg["From"] = config.MAIL_FROM_ADDRESS
        msg["To"] = to_email

        with smtplib.SMTP(config.MAIL_HOST, config.MAIL_PORT) as server:
 
            if config.MAIL_ENCRYPTION == "TLS":
                server.starttls()
               
            server.login(config.MAIL_USERNAME, config.MAIL_PASSWORD)
            server.sendmail(config.MAIL_FROM_ADDRESS, [to_email], msg.as_string())
    except Exception as e:
        logging.error(f"Failed to send email: {e}")