import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.platform.config import MAIL_FROM_ADDRESS, MAIL_HOST, MAIL_PORT, MAIL_USERNAME, MAIL_PASSWORD, MAIL_ENCRYPTION

def send_email(to_email: str, subject: str, body: str):
    msg = MIMEText(body, 'html')
    msg["Subject"] = subject
    msg["From"] = MAIL_FROM_ADDRESS
    msg["To"] = to_email

    with smtplib.SMTP(MAIL_HOST, MAIL_PORT) as server:
        if MAIL_ENCRYPTION == "TLS":
            server.starttls()
        server.login(MAIL_USERNAME, MAIL_PASSWORD)
        server.sendmail(MAIL_FROM_ADDRESS, [to_email], msg.as_string())


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


def send_password_reset_email(to_email: str, reset_token: str):
    """Send password reset email to user"""
    subject = "Reset Your Password - Site Audit AI"

    
    reset_link = f"https://yourapp.com/reset-password?token={reset_token}&email={to_email}"

    body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #FF6B35;">Password Reset Request</h2>
                <p>Hi there,</p>
                <p>We received a request to reset your password for your Site Audit AI account. If you made this request, click the button below to reset your password:</p>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_link}"
                       style="background-color: #FF6B35;
                              color: white;
                              padding: 12px 30px;
                              text-decoration: none;
                              border-radius: 5px;
                              font-weight: bold;
                              display: inline-block;">
                        Reset Password
                    </a>
                </div>

                <p style="color: #666; font-size: 14px;">
                    <strong>Important:</strong> This link will expire in <strong>1 minute</strong> for security reasons.
                </p>

                <p style="color: #666; font-size: 14px;">
                    If you didn't request a password reset, please ignore this email. Your password will remain unchanged.
                </p>

                <p style="color: #666; font-size: 14px;">
                    If the button doesn't work, copy and paste this link into your browser:<br>
                    <a href="{reset_link}" style="color: #FF6B35; word-break: break-all;">{reset_link}</a>
                </p>

                <p style="color: #999; font-size: 12px; margin-top: 30px;">
                    <strong>Security Tip:</strong> Never share this link with anyone. Site Audit AI will never ask for your password.
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