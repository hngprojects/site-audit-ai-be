
from typing import Dict, List, Optional
from enum import Enum
import requests
import json
from datetime import datetime
import os


class NotificationType(str, Enum):
    """Types of notifications"""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    WEBHOOK = "webhook"


class NotificationService:
    """Service for sending various types of notifications"""
    
    def __init__(self, email_service=None):
        """
        Initialize notification service
        
        Args:
            email_service: EmailService instance for sending emails
        """
        self.email_service = email_service
        self.notification_log = []  # In-memory log; use database in production
    
    def send_notification(
        self,
        notification_type: str,
        recipient: str,
        subject: str,
        message: str,
        data: Optional[Dict] = None
    ) -> bool:
        notification_type = NotificationType(notification_type)
        
        result = False
        
        if notification_type == NotificationType.EMAIL:
            result = self._send_email_notification(recipient, subject, message, data)
        elif notification_type == NotificationType.SMS:
            result = self._send_sms_notification(recipient, message)
        elif notification_type == NotificationType.PUSH:
            result = self._send_push_notification(recipient, subject, message, data)
        elif notification_type == NotificationType.WEBHOOK:
            result = self._send_webhook_notification(recipient, data)
        elif notification_type == NotificationType.SLACK:
            result = self._send_slack_notification(recipient, message, data)
        
        # Log notification
        self._log_notification(
            notification_type=notification_type.value,
            recipient=recipient,
            subject=subject,
            success=result
        )
        
        return result
    
    def _send_email_notification(
        self,
        email: str,
        subject: str,
        message: str,
        data: Optional[Dict] = None
    ) -> bool:
        if not self.email_service:
            print("Email service not configured")
            return False
        
        # Simple HTML wrapper
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <body>
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                {message}
            </div>
        </body>
        </html>
        """
        
        return self.email_service.send_email(
            to_email=email,
            subject=subject,
            body_html=html_body,
            body_text=message
        )
    
    def _send_sms_notification(self, phone: str, message: str) -> bool:
        try:
            # Example using Twilio (requires twilio package and credentials)
            # from twilio.rest import Client
            # client = Client(account_sid, auth_token)
            # message = client.messages.create(
            #     body=message,
            #     from_='+1234567890',
            #     to=phone
            # )
            
            print(f"SMS sent to {phone}: {message}")
            return True
        
        except Exception as e:
            print(f"Failed to send SMS: {str(e)}")
            return False
    
    def _send_push_notification(
        self,
        device_token: str,
        title: str,
        message: str,
        data: Optional[Dict] = None
    ) -> bool:
        try:
            # Example using Firebase Cloud Messaging
            # Would require firebase-admin package
            
            print(f"Push notification sent: {title} - {message}")
            return True
        
        except Exception as e:
            print(f"Failed to send push notification: {str(e)}")
            return False
    
    def _send_webhook_notification(self, webhook_url: str, data: Dict) -> bool:
        try:
            response = requests.post(
                webhook_url,
                json=data,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            return response.status_code in [200, 201, 204]
        
        except Exception as e:
            print(f"Failed to send webhook: {str(e)}")
            return False
    
    
    def notify_new_ticket(self, ticket_data: Dict) -> bool:
        results = []
        
        # Email to user
        if self.email_service:
            user_result = self.email_service.send_ticket_confirmation(ticket_data)
            results.append(user_result)
        
        # Email to support team
        if self.email_service:
            team_result = self.email_service.notify_support_team(ticket_data)
            results.append(team_result)
        
        return all(results) if results else False
    
    def notify_ticket_update(self, ticket_data: Dict, update_message: str) -> bool:
        """
        Send notifications for ticket update
        
        Args:
            ticket_data: Ticket information
            update_message: Update message
            
        Returns:
            True if notification sent successfully
        """
        if self.email_service:
            return self.email_service.send_ticket_update(ticket_data, update_message)
        return False
    
    def notify_chat_started(self, session_data: Dict) -> bool:
        """
        Send notification when chat session starts
        
        Args:
            session_data: Chat session information
            
        Returns:
            True if notification sent successfully
        """
        # Could send SMS or push notification
        return True
    
    def notify_agent_assigned(self, session_data: Dict, agent_data: Dict) -> bool:
        """
        Notify user when agent is assigned to their chat
        
        Args:
            session_data: Chat session information
            agent_data: Agent information
            
        Returns:
            True if notification sent successfully
        """
        # Could send push notification or update UI via websocket
        return True
    
    def send_chat_transcript(self, session_data: Dict, messages: List[Dict]) -> bool:
        """
        Send chat transcript to user
        
        Args:
            session_data: Chat session information
            messages: List of chat messages
            
        Returns:
            True if transcript sent successfully
        """
        if self.email_service:
            return self.email_service.send_chat_transcript(session_data, messages)
        return False
    
    def notify_support_team(
        self,
        subject: str,
        message: str,
        priority: str = "medium",
        data: Optional[Dict] = None
    ) -> bool:
    
        # Send email to admin
        if  not self.email_service:
            print ("Email servicee not configured")
            return False
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 700px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #FF5C4D; color: white; padding: 20px; }}
                .content {{ background-color: #f9f9f9; padding: 20px; }}
                .data-box {{ background-color: white; padding: 15px; margin: 15px 0; border: 1px solid #ddd; }}
                .footer {{ text-align: center; padding: 10px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2> {subject}</h2>
                    <p style="margin: 0;">Priority: {priority.upper()}</p>
                </div>
                <div class="content">
                    <p>{message}</p>
                    
                    {f'''
                    <div class="data-box">
                        <h3>Additional Details:</h3>
                        <pre>{json.dumps(data, indent=2)}</pre>
                    </div>
                    ''' if data else ''}
                </div>
                <div class="footer">
                    <p>Tokugawa Support System | admin@tokugawa.emerj.net</p>
                    <p>This is an automated notification from tokugawa.emerj.net</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self.email_service.send_email(
            to_email='admin@tokugawa.emerj.net',
            subject=f"[Tokugawa] {subject}",
            body_html=html_body,
            body_text=f"{subject}\n\n{message}"
        )
    
    def _log_notification(
        self,
        notification_type: str,
        recipient: str,
        subject: str,
        success: bool
    ):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'type': notification_type,
            'recipient': recipient,
            'subject': subject,
            'success': success
        }
        
        self.notification_log.append(log_entry)
        
        # In production, save to database
        # db.add(NotificationLog(**log_entry))
        # db.commit()
    
    def get_notification_history(self, limit: int = 100) -> List[Dict]:
        return self.notification_log[-limit:]