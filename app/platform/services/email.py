import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from jinja2 import Environment, FileSystemLoader
from app.platform.config import MAIL_FROM_ADDRESS, MAIL_HOST, MAIL_PORT, MAIL_USERNAME, MAIL_PASSWORD, MAIL_ENCRYPTION, MAIL_FROM_NAME  
from app.platform.logger import get_logger


# 1. SETUP JINJA2 TEMPLATE LOADER
current_dir = os.path.dirname(os.path.abspath(__file__))

template_dir = os.path.join(current_dir, "../template") 

if not os.path.exists(template_dir):
    template_dir = "app/platform/template"

env = Environment(loader=FileSystemLoader(template_dir))

logger = get_logger("email_service")

def send_email(to_email: str, subject: str, body: str):
    """Base function to send email via SMTP"""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = MAIL_FROM_ADDRESS
    msg["To"] = to_email

    msg.attach(MIMEText(body, 'html'))

    try:
        with smtplib.SMTP(MAIL_HOST, MAIL_PORT) as server:
            server.ehlo()
            if str(MAIL_ENCRYPTION).upper() == "TLS":
                server.starttls()
                server.ehlo()
            server.login(MAIL_USERNAME, MAIL_PASSWORD)
            server.sendmail(MAIL_FROM_ADDRESS, to_email, msg.as_string())

        logger.info(f"Email sent to {to_email} with subject '{subject}'")

    except Exception as e:
        print(f"Failed to send email to {to_email}: {e}")
        logger.error(f"Failed to send email to {to_email}: {e}")
     
# SPECIFIC EMAIL FUNCTIONS (Using Templates)

def send_verification_otp(to_email: str, first_name: str, otp: str):
    """Sends the 'Verify Account Deletion' or 'Verify Signup' email"""
    # Load the specific template file
    template = env.get_template("verification_code.html")
    
    # Inject the data into the {{ variables }}
    html_content = template.render(
        first_name=first_name,
        otp_code=otp,
        expiration_minutes="10"
    )
    
    send_email(to_email, "Verify Your Identity - Sitelytics", html_content)


def send_password_reset(to_email: str, first_name: str, otp: str):
    """Sends the Forgot Password email"""
    template = env.get_template("reset_password.html")
    
    html_content = template.render(
        first_name=first_name,
        otp_code=otp,
        expiration_minutes="10"
    )
    
    send_email(to_email, "Reset Your Password - Sitelytics", html_content)


def send_welcome_email(to_email: str, first_name: str):
    """Sends the Waitlist Welcome email"""
    template = env.get_template("welcome_email.html")
    
    html_content = template.render(
        first_name=first_name,
        dashboard_url="https://sitelytics.com/dashboard" # Update with real URL
    )
    
    send_email(to_email, "You're on the list! - Sitelytics", html_content)


def send_account_activation(to_email: str, first_name: str):
    """Sends the 'Welcome to Dashboard' email"""
    template = env.get_template("welcome_activation.html")
    
    html_content = template.render(
        first_name=first_name,
        action_url="https://sitelytics.com/get-review" # Update with real URL
    )
    
    send_email(to_email, "Welcome to Sitelytics", html_content)
    
def review_request_email(to_email: str, first_name: str, site_name: str, review_link: str):
    """Sends the 'Request Review' email"""
    template = env.get_template("review_request_confirmation.html")
    
    html_content = template.render(
        first_name=first_name,
        site_name=site_name,
        review_link=review_link
    )
    
    send_email(to_email, f"Review Request for {site_name} - Sitelytics", html_content)