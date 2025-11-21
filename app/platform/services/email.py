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
template_dir = os.path.join(current_dir, "../template")

if not os.path.exists(template_dir):
    template_dir = os.path.join(os.getcwd(), "app/platform/template")

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



def send_verification_otp(to_email: str, first_name: str, otp: str):
    """Used for: Account Deletion Verification"""
    template = env.get_template("verification_code.html")
    html_content = template.render(
        first_name=first_name,
        otp_code=otp,
        expiration_minutes="10"
    )
    send_email(to_email, "Verify Your Identity - Sitelytics", html_content)


def send_signup_verification(to_email: str, first_name: str, otp: str):
    """Used for: New User Signup Verification"""
    template = env.get_template("verify_signup.html")
    html_content = template.render(
        first_name=first_name,
        otp_code=otp,
        expiration_minutes="10"
    )
    send_email(to_email, "Verify Your Email - Sitelytics", html_content)


def send_password_reset(to_email: str, first_name: str, otp: str):
    """Used for: Forgot Password"""
    template = env.get_template("reset_password.html")
    html_content = template.render(
        first_name=first_name,
        otp_code=otp,
        expiration_minutes="10"
    )
    send_email(to_email, "Reset Your Password - Sitelytics", html_content)


def send_welcome_email(to_email: str, first_name: str):
    """Used for: Waitlist Confirmation"""
    template = env.get_template("welcome_email.html")
    html_content = template.render(
        first_name=first_name,
        dashboard_url="https://sitelytics.com/dashboard"
    )
    send_email(to_email, "You're on the list! - Sitelytics", html_content)


def send_account_activation(to_email: str, first_name: str):
    """Used for: Welcome Dashboard (After Signup Verification)"""
    template = env.get_template("welcome_activation.html")
    html_content = template.render(
        first_name=first_name,
        action_url="https://sitelytics.com/get-review"
    )
    send_email(to_email, "Welcome to Sitelytics", html_content)

    
def review_request_email(to_email: str, first_name: str, site_name: str, review_link: str):
    """Used for: Audit/Review Requests"""
    template = env.get_template("review_request_confirmation.html")
    html_content = template.render(
        first_name=first_name,
        site_name=site_name,
        review_link=review_link,
        dashboard_url="https://sitelytics.com/dashboard"
    )
    send_email(to_email, f"Review Request for {site_name}", html_content)


def send_account_deleted(to_email: str, first_name: str):
    """Used for: Successful Deletion Notification"""
    template = env.get_template("account_deleted.html")
    html_content = template.render(
        first_name=first_name
    )
    send_email(to_email, "Your Account Has Been Deleted", html_content)
    