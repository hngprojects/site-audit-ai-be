import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
from app.platform import config

logger = logging.getLogger(__name__)


async def send_password_reset_email(to_email: str, reset_token: str) -> bool:
    try:
        reset_link = f"{config.FRONTEND_URL}/reset-password?token={reset_token}"
        
        from_email = Email(config.MAIL_FROM_ADDRESS, config.MAIL_FROM_NAME)
        to_email_obj = To(to_email)
        subject = "Password Reset Request"
        
        html_content = f"""
        <html>
            <body>
                <h2>Password Reset Request</h2>
                <p>You have requested to reset your password.</p>
                <p>Please click the link below to reset your password:</p>
                <p><a href="{reset_link}" style="display: inline-block; padding: 10px 20px; background-color: #007bff; color: white; text-decoration: none; border-radius: 5px;">Reset Password</a></p>
                <p>Or copy and paste this link in your browser:</p>
                <p>{reset_link}</p>
                <p><strong>This link will expire in 30 minutes.</strong></p>
                <p>If you did not request a password reset, please ignore this email.</p>
                <br>
                <p>Best regards,<br>{config.MAIL_FROM_NAME}</p>
            </body>
        </html>
        """
        
        plain_content = f"""
        Password Reset Request
        
        You have requested to reset your password.
        
        Please use the following link to reset your password:
        {reset_link}
        
        This link will expire in 30 minutes.
        
        If you did not request a password reset, please ignore this email.
        
        Best regards,
        {config.MAIL_FROM_NAME}
        """
        
        message = Mail(
            from_email=from_email,
            to_emails=to_email_obj,
            subject=subject,
            plain_text_content=plain_content,
            html_content=html_content
        )
        
        sg = SendGridAPIClient(config.SENDGRID_API_KEY)
        response = sg.send(message)
        
        if response.status_code >= 200 and response.status_code < 300:
            logger.info(f"Password reset email sent successfully to {to_email}")
            return True
        else:
            logger.error(f"Failed to send email. Status code: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"Error sending password reset email: {str(e)}")
        return False


async def send_password_reset_confirmation_email(to_email: str) -> bool:

    try:
        from_email = Email(config.MAIL_FROM_ADDRESS, config.MAIL_FROM_NAME)
        to_email_obj = To(to_email)
        subject = "Password Reset Successful"
        
        html_content = f"""
        <html>
            <body>
                <h2>Password Reset Successful</h2>
                <p>Your password has been successfully reset.</p>
                <p>If you did not perform this action, please contact support immediately.</p>
                <br>
                <p>Best regards,<br>{config.MAIL_FROM_NAME}</p>
            </body>
        </html>
        """
        
        plain_content = f"""
        Password Reset Successful
        
        Your password has been successfully reset.
        
        If you did not perform this action, please contact support immediately.
        
        Best regards,
        {config.MAIL_FROM_NAME}
        """
        
        message = Mail(
            from_email=from_email,
            to_emails=to_email_obj,
            subject=subject,
            plain_text_content=plain_content,
            html_content=html_content
        )
        
        sg = SendGridAPIClient(config.SENDGRID_API_KEY)
        response = sg.send(message)
        
        if response.status_code >= 200 and response.status_code < 300:
            logger.info(f"Password reset confirmation email sent to {to_email}")
            return True
        else:
            logger.error(f"Failed to send confirmation email. Status code: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"Error sending password reset confirmation email: {str(e)}")
        return False
