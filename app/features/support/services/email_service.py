import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional
from datetime import datetime
import os
from jinja2 import Environment, FileSystemLoader, select_autoescape


class EmailService:
    """Service for sending and managing emails"""
    
    def __init__(self):
        """Initialize email service with SMTP configuration"""
        self.smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', 587))
        self.smtp_username = os.getenv('SMTP_USERNAME', '')
        self.smtp_password = os.getenv('SMTP_PASSWORD', '')
        self.sender_email = os.getenv('SENDER_EMAIL', 'support@tokugawa.emerj.net')
        self.sender_name = os.getenv('SENDER_NAME', ' Tokugawa Support Team')
        self.support_email = os.getenv('SUPPORT_EMAIL', 'admin@tokugawa.emerj.net')
        
        # Template environment
        template_path = os.path.join(os.path.dirname(__file__), '../templates/email')
        self.jinja_env = Environment(
            loader=FileSystemLoader(template_path) if os.path.exists(template_path) else None,
            autoescape=select_autoescape(['html', 'xml'])
        )
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        body_html: str,
        body_text: Optional[str] = None,
        reply_to: Optional[str] = None
    ) -> bool:
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.sender_name} <{self.sender_email}>"
            msg['To'] = to_email
            msg['Subject'] = subject
            
            if reply_to:
                msg['Reply-To'] = reply_to
            
            # Attach plain text version
            if body_text:
                msg.attach(MIMEText(body_text, 'plain'))
            
            # Attach HTML version
            msg.attach(MIMEText(body_html, 'html'))
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            return True
        
        except Exception as e:
            print(f"Failed to send email: {str(e)}")
            return False
    
    def send_ticket_confirmation(self, ticket_data: Dict) -> bool:
        subject = f"Ticket Received: {ticket_data['ticket_id']}"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #FF5C4D; color: white; padding: 20px; text-align: center; }}
                .content {{ background-color: #f9f9f9; padding: 20px; }}
                .ticket-info {{ background-color: white; padding: 15px; margin: 15px 0; border-left: 4px solid #FF5C4D; }}
                .footer {{ text-align: center; padding: 20px; font-size: 12px; color: #666; }}
                .button {{ 
                    display: inline-block; 
                    background-color: #FF5C4D; 
                    color: white; 
                    padding: 12px 30px; 
                    text-decoration: none; 
                    border-radius: 5px;
                    margin: 15px 0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>✓ We've Received Your Message</h1>
                </div>
                <div class="content">
                    <p>Hi {ticket_data['name']},</p>
                    <p>Thank you for reaching out to our support team. We've received your message and will respond within 24 hours.</p>
                    
                    <div class="ticket-info">
                        <strong>Ticket ID:</strong> {ticket_data['ticket_id']}<br>
                        <strong>Subject:</strong> {ticket_data['subject']}<br>
                        <strong>Created:</strong> {datetime.utcnow().strftime('%B %d, %Y at %I:%M %p UTC')}<br>
                        <strong>Status:</strong> Pending
                    </div>
                    
                    <p><strong>Your Message:</strong></p>
                    <p style="background-color: white; padding: 15px; border: 1px solid #ddd;">
                        {ticket_data['message'][:500]}{'...' if len(ticket_data['message']) > 500 else ''}
                    </p>
                    
                    <p style="text-align: center;">
                        <a href="#" class="button">Track Your Ticket</a>
                    </p>
                    
                    <p>You can reply directly to this email to add more information to your ticket.</p>
                </div>
                <div class="footer">
                    <p>This is an automated message. Please do not reply to this email.</p>
                    <p>Need immediate assistance? Visit our <a href="#">Help Center</a></p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_body = f"""
        We've Received Your Message
        
        Hi {ticket_data['name']},
        
        Thank you for reaching out to our support team. We've received your message and will respond within 24 hours.
        
        Ticket ID: {ticket_data['ticket_id']}
        Subject: {ticket_data['subject']}
        Created: {datetime.utcnow().strftime('%B %d, %Y at %I:%M %p UTC')}
        Status: Pending
        
        Your Message:
        {ticket_data['message'][:500]}{'...' if len(ticket_data['message']) > 500 else ''}
        
        You can reply directly to this email to add more information to your ticket.
        
        Need immediate assistance? Visit our Help Center
        """
        
        return self.send_email(
            to_email=ticket_data['email'],
            subject=subject,
            body_html=html_body,
            body_text=text_body,
            reply_to=self.support_email
        )
    
    def send_message_confirmation(self, message_data: Dict) -> bool:
        subject = "Message Sent Successfully"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
                .content {{ background-color: #f9f9f9; padding: 20px; }}
                .footer {{ text-align: center; padding: 20px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>✓ Message Sent!</h1>
                </div>
                <div class="content">
                    <p>Hi {message_data['name']},</p>
                    <p>Thank you for reaching out. We'll get back to you at <strong>{message_data['email']}</strong> within 24 hours.</p>
                    <p>Our team is reviewing your message and will respond as soon as possible.</p>
                </div>
                <div class="footer">
                    <p>This is an automated confirmation. Please do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_body = f"""
        Message Sent!
        
        Hi {message_data['name']},
        
        Thank you for reaching out. We'll get back to you at {message_data['email']} within 24 hours.
        
        Our team is reviewing your message and will respond as soon as possible.
        """
        
        return self.send_email(
            to_email=message_data['email'],
            subject=subject,
            body_html=html_body,
            body_text=text_body
        )
    
    def send_ticket_update(self, ticket_data: Dict, update_message: str) -> bool:
        subject = f"Ticket Update: {ticket_data['ticket_id']}"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #2196F3; color: white; padding: 20px; text-align: center; }}
                .content {{ background-color: #f9f9f9; padding: 20px; }}
                .update {{ background-color: white; padding: 15px; margin: 15px 0; border-left: 4px solid #2196F3; }}
                .footer {{ text-align: center; padding: 20px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Ticket Update</h1>
                </div>
                <div class="content">
                    <p>Hi {ticket_data['name']},</p>
                    <p>There's an update on your support ticket:</p>
                    
                    <div class="update">
                        <strong>Ticket ID:</strong> {ticket_data['ticket_id']}<br>
                        <strong>Status:</strong> {ticket_data.get('status', 'In Progress')}<br><br>
                        <p>{update_message}</p>
                    </div>
                    
                    <p>You can reply directly to this email to continue the conversation.</p>
                </div>
                <div class="footer">
                    <p>Support Team | {self.support_email}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(
            to_email=ticket_data['email'],
            subject=subject,
            body_html=html_body,
            reply_to=self.support_email
        )
    
    def notify_support_team(self, ticket_data: Dict) -> bool:
        subject = f"New Support Ticket: {ticket_data['ticket_id']}"
        
        priority_colors = {
            'urgent': '#FF0000',
            'high': '#FF5C4D',
            'medium': '#FFA500',
            'low': '#4CAF50'
        }
        
        priority = ticket_data.get('priority', 'medium')
        color = priority_colors.get(priority, '#FFA500')
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 700px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: {color}; color: white; padding: 20px; }}
                .content {{ background-color: #f9f9f9; padding: 20px; }}
                .ticket-details {{ background-color: white; padding: 15px; margin: 15px 0; }}
                table {{ width: 100%; border-collapse: collapse; }}
                th {{ text-align: left; padding: 8px; background-color: #f0f0f0; }}
                td {{ padding: 8px; border-bottom: 1px solid #ddd; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>🎫 New Support Ticket</h2>
                    <p style="margin: 0;">Priority: {priority.upper()}</p>
                </div>
                <div class="content">
                    <div class="ticket-details">
                        <table>
                            <tr>
                                <th>Ticket ID:</th>
                                <td>{ticket_data['ticket_id']}</td>
                            </tr>
                            <tr>
                                <th>From:</th>
                                <td>{ticket_data['name']} ({ticket_data['email']})</td>
                            </tr>
                            <tr>
                                <th>Subject:</th>
                                <td>{ticket_data['subject']}</td>
                            </tr>
                            <tr>
                                <th>Created:</th>
                                <td>{datetime.utcnow().strftime('%B %d, %Y at %I:%M %p UTC')}</td>
                            </tr>
                            <tr>
                                <th>Type:</th>
                                <td>{ticket_data.get('ticket_type', 'email')}</td>
                            </tr>
                        </table>
                    </div>
                    
                    <h3>Message:</h3>
                    <div style="background-color: white; padding: 15px; border: 1px solid #ddd;">
                        {ticket_data['message']}
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(
            to_email='admin@tokugawa.emerj.net',
            subject=subject,
            body_html=html_body
        )
    
    def send_chat_transcript(self, session_data: Dict, messages: List[Dict]) -> bool:
        subject = f"Chat Transcript - {session_data['session_id']}"
        
        # Build message list HTML
        messages_html = ""
        for msg in messages:
            sender = msg.get('sender_name', 'Unknown')
            time = msg.get('sent_at', '')
            content = msg.get('content', '')
            
            messages_html += f"""
            <div style="margin: 10px 0; padding: 10px; background-color: {'#f0f0f0' if msg['sender_type'] == 'user' else '#e3f2fd'};">
                <strong>{sender}</strong> <small style="color: #666;">{time}</small><br>
                {content}
            </div>
            """
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 700px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #673AB7; color: white; padding: 20px; text-align: center; }}
                .content {{ background-color: #f9f9f9; padding: 20px; }}
                .transcript {{ background-color: white; padding: 15px; max-height: 500px; overflow-y: auto; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Chat Transcript</h1>
                </div>
                <div class="content">
                    <p>Thank you for chatting with our support team. Here's a transcript of your conversation:</p>
                    
                    <div class="transcript">
                        {messages_html}
                    </div>
                    
                    <p style="margin-top: 20px;">If you have any additional questions, feel free to reach out again!</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(
            to_email=session_data.get('user_email'),
            subject=subject,
            body_html=html_body
        )