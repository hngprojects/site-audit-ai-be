import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.platform.config import settings


def send_email(to_email: str, subject: str, body: str):
    """
    Send an HTML email using SMTP with proper TLS/SSL handling.
    
    MAIL_ENCRYPTION should be one of: "SSL", "TLS", or None.
    MAIL_PORT must match the encryption type:
        SSL -> 465
        TLS -> 587
        None -> 25 or custom
    """
    print("Email reached here:", body)

    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = settings.MAIL_FROM_ADDRESS
    msg["To"] = to_email
    msg.attach(MIMEText(body, "html"))

    try:
        if settings.MAIL_ENCRYPTION.upper() == "SSL":
            server = smtplib.SMTP_SSL(settings.MAIL_HOST, settings.MAIL_PORT)

        else:
            server = smtplib.SMTP(settings.MAIL_HOST, settings.MAIL_PORT)
            server.ehlo()
            if settings.MAIL_ENCRYPTION.upper() == "TLS":
                server.starttls()
                server.ehlo()

        # Login
        server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)

        # Send email
        server.sendmail(settings.MAIL_FROM_ADDRESS, [to_email], msg.as_string())
        server.quit()

        print(f"Email sent to {to_email}")

    except Exception as e:
        print(f"Failed to send email to {to_email}: {e}")
        raise


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



    """Send password reset email to user"""
    subject = "Password Reset Request - Site Audit AI"

    body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #FF6B35;">Password Reset Request</h2>
                <p>Hi there,</p>
                <p>We received a request to reset your password for your Site Audit AI account. If you made this request, please use the OTP code below:</p>

                <div style="text-align: center; margin: 30px 0;">
                    <div style="background-color: #f5f5f5; 
                                padding: 20px; 
                                border-radius: 10px;
                                display: inline-block;">
                        <p style="margin: 0; font-size: 14px; color: #666;">Your OTP Code</p>
                        <h1 style="margin: 10px 0; 
                                   font-size: 36px; 
                                   letter-spacing: 8px;
                                   color: #FF6B35;
                                   font-weight: bold;">{otp}</h1>
                    </div>
                </div>

                <p style="color: #666; font-size: 14px; margin-top: 30px;">
                    This OTP will expire in <strong>10 minutes</strong>. If you didn't request a password reset, please ignore this email.
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