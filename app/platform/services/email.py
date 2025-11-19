import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.platform.config import MAIL_FROM_ADDRESS, MAIL_HOST, MAIL_PORT, MAIL_USERNAME, MAIL_PASSWORD, MAIL_ENCRYPTION
import httpx

def send_email(to_email: str, subject: str, body: str):

    
    try:

        form_data = {
            "subject": subject,
            "recipients": [to_email],
            "body": body,
        }
        

        response = httpx.post(
            "http://3.232.57.58/crunch-email",
            data={
                "subject": form_data["subject"],
                "recipients": form_data["recipients"],
                "body": form_data["body"],
            },
            timeout=30.0
        )
        response.raise_for_status()
        
    except Exception as e:
        print(f"Failed to send email via external service: {e}")
        raise
    
    # ORIGINAL SMTP IMPLEMENTATION (COMMENTED OUT FOR PATCH)
    # msg = MIMEText(body, 'html')
    # msg["Subject"] = subject
    # msg["From"] = MAIL_FROM_ADDRESS
    # msg["To"] = to_email

    # with smtplib.SMTP(MAIL_HOST, MAIL_PORT) as server:
    #     if MAIL_ENCRYPTION == "TLS":
    #         server.starttls()
    #     server.login(MAIL_USERNAME, MAIL_PASSWORD)
    #     server.sendmail(MAIL_FROM_ADDRESS, [to_email], msg.as_string())


def send_verification_otp(to_email: str, username: str, otp: str):
    """Send OTP verification email to user"""
    subject = "Verify Your Email Address - OTP Code"
    
    body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #4CAF50;">Welcome to Site Audit AI! 🎉</h2>
                <p>Hi <strong>{username}</strong>,</p>
                <p>Thanks for signing up! Please use the OTP code below to verify your email address:</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <div style="background-color: #f5f5f5; 
                                padding: 20px; 
                                border-radius: 10px;
                                display: inline-block;">
                        <p style="margin: 0; font-size: 14px; color: #666;">Your OTP Code</p>
                        <h1 style="margin: 10px 0; 
                                   font-size: 36px; 
                                   letter-spacing: 8px;
                                   color: #4CAF50;
                                   font-weight: bold;">{otp}</h1>
                    </div>
                </div>
                
                <p style="color: #666; font-size: 14px; margin-top: 30px;">
                    This OTP will expire in <strong>10 minutes</strong>. If you didn't create an account, please ignore this email.
                </p>
                
                <p style="color: #999; font-size: 12px; margin-top: 20px;">
                    <strong>Security Tip:</strong> Never share this OTP with anyone. Site Audit AI will never ask for your OTP via phone or email.
                </p>
                
                <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                <p style="color: #999; font-size: 12px;">
                    &copy; 2025 Site Audit AI. All rights reserved.
                </p>
            </div>
        </body>
    </html>
    """
    
    send_email(to_email, subject, body)