import smtplib
from email.mime.text import MIMEText
from app.platform.config import MAIL_FROM_ADDRESS, MAIL_HOST, MAIL_PORT, MAIL_USERNAME, MAIL_PASSWORD, MAIL_ENCRYPTION

def send_email(to_email: str, subject: str, body: str):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = MAIL_FROM_ADDRESS
    msg["To"] = to_email

    with smtplib.SMTP(MAIL_HOST, MAIL_PORT) as server:
        if MAIL_ENCRYPTION == "TLS":
            server.starttls()
        server.login(MAIL_USERNAME, MAIL_PASSWORD)
        server.sendmail(MAIL_FROM_ADDRESS, [to_email], msg.as_string())