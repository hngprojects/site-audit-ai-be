import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import bleach


class ValidationService:
    """Service for validating and sanitizing user inputs"""
    
    # Email regex pattern (RFC 5322 simplified)
    EMAIL_PATTERN = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )
    
    # Phone number pattern (international format)
    PHONE_PATTERN = re.compile(
        r'^\+?[1-9]\d{1,14}$'
    )
    
    # Allowed HTML tags for message sanitization
    ALLOWED_TAGS = ['p', 'br', 'strong', 'em', 'u', 'a', 'ul', 'ol', 'li']
    ALLOWED_ATTRIBUTES = {'a': ['href', 'title']}
    
    # Field length constraints
    MAX_NAME_LENGTH = 255
    MAX_EMAIL_LENGTH = 255
    MAX_SUBJECT_LENGTH = 500
    MAX_MESSAGE_LENGTH = 5000
    MIN_MESSAGE_LENGTH = 10
    MAX_PHONE_LENGTH = 50
    
    @staticmethod
    def validate_email(email: str) -> Tuple[bool, Optional[str]]:
        if not email:
            return False, "Email is required"
        
        email = email.strip()
        
        if len(email) > ValidationService.MAX_EMAIL_LENGTH:
            return False, f"Email must not exceed {ValidationService.MAX_EMAIL_LENGTH} characters"
        
        if not ValidationService.EMAIL_PATTERN.match(email):
            return False, "Invalid email format"
        
        # Check for common typos
        common_domains = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com']
        domain = email.split('@')[-1].lower()
        
        # Basic typo detection (e.g., gmial.com)
        typo_suggestions = {
            'gmial.com': 'gmail.com',
            'gmai.com': 'gmail.com',
            'yahooo.com': 'yahoo.com',
            'hotmial.com': 'hotmail.com'
        }
        
        if domain in typo_suggestions:
            return False, f"Did you mean {typo_suggestions[domain]}?"
        
        return True, None
    
    @staticmethod
    def validate_name(name: str) -> Tuple[bool, Optional[str]]:
        if not name:
            return False, "Name is required"
        
        name = name.strip()
        
        if len(name) < 2:
            return False, "Name must be at least 2 characters"
        
        if len(name) > ValidationService.MAX_NAME_LENGTH:
            return False, f"Name must not exceed {ValidationService.MAX_NAME_LENGTH} characters"
        
        # Check for invalid characters (allow letters, spaces, hyphens, apostrophes)
        if not re.match(r"^[a-zA-Z\s\-'\.]+$", name):
            return False, "Name contains invalid characters"
        
        return True, None
    
    @staticmethod
    def validate_subject(subject: str) -> Tuple[bool, Optional[str]]:
        if not subject:
            return False, "Subject is required"
        
        subject = subject.strip()
        
        if len(subject) < 3:
            return False, "Subject must be at least 3 characters"
        
        if len(subject) > ValidationService.MAX_SUBJECT_LENGTH:
            return False, f"Subject must not exceed {ValidationService.MAX_SUBJECT_LENGTH} characters"
        
        return True, None
    
    @staticmethod
    def validate_message(message: str) -> Tuple[bool, Optional[str]]:
        if not message:
            return False, "Message is required"
        
        message = message.strip()
        
        if len(message) < ValidationService.MIN_MESSAGE_LENGTH:
            return False, f"Message must be at least {ValidationService.MIN_MESSAGE_LENGTH} characters"
        
        if len(message) > ValidationService.MAX_MESSAGE_LENGTH:
            return False, f"Message must not exceed {ValidationService.MAX_MESSAGE_LENGTH} characters"
        
        return True, None
    
    @staticmethod
    def validate_phone(phone: str) -> Tuple[bool, Optional[str]]:
        if not phone:
            return True, None  # Phone is optional
        
        # Remove common formatting characters
        phone_cleaned = re.sub(r'[\s\-\(\)]', '', phone)
        
        if len(phone_cleaned) > ValidationService.MAX_PHONE_LENGTH:
            return False, f"Phone number must not exceed {ValidationService.MAX_PHONE_LENGTH} characters"
        
        # Basic phone validation
        if not re.match(r'^\+?[\d\s\-\(\)]+$', phone):
            return False, "Invalid phone number format"
        
        return True, None
    
    @staticmethod
    def sanitize_html(content: str) -> str:
        return bleach.clean(
            content,
            tags=ValidationService.ALLOWED_TAGS,
            attributes=ValidationService.ALLOWED_ATTRIBUTES,
            strip=True
        )
    
    @staticmethod
    def sanitize_text(text: str) -> str:
        if not text:
            return ""
        
        # Remove control characters except newlines and tabs
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        
        # Trim whitespace
        text = text.strip()
        
        return text
    
    @staticmethod
    def validate_support_request(data: Dict) -> Tuple[bool, Dict[str, List[str]]]:
        errors = {}
        
        # Validate name
        if 'name' in data:
            is_valid, error = ValidationService.validate_name(data['name'])
            if not is_valid:
                errors['name'] = [error]
        
        # Validate email
        if 'email' in data:
            is_valid, error = ValidationService.validate_email(data['email'])
            if not is_valid:
                errors['email'] = [error]
        
        # Validate subject
        if 'subject' in data:
            is_valid, error = ValidationService.validate_subject(data['subject'])
            if not is_valid:
                errors['subject'] = [error]
        
        # Validate message
        if 'message' in data:
            is_valid, error = ValidationService.validate_message(data['message'])
            if not is_valid:
                errors['message'] = [error]
        
        # Validate phone (if provided)
        if 'phone' in data and data['phone']:
            is_valid, error = ValidationService.validate_phone(data['phone'])
            if not is_valid:
                errors['phone'] = [error]
        
        return len(errors) == 0, errors
    
    @staticmethod
    def check_spam_indicators(data: Dict) -> Tuple[bool, List[str]]:
        spam_reasons = []
        
        message = data.get('message', '').lower()
        subject = data.get('subject', '').lower()
        
        # Check for excessive URLs
        url_pattern = r'https?://\S+|www\.\S+'
        urls = re.findall(url_pattern, message + ' ' + subject)
        if len(urls) > 3:
            spam_reasons.append("Excessive URLs detected")
        
        # Check for spam keywords
        spam_keywords = [
            'viagra', 'cialis', 'casino', 'lottery', 'winner',
            'click here', 'act now', 'limited time', 'make money fast',
            'work from home', 'nigerian prince', 'inheritance'
        ]
        
        for keyword in spam_keywords:
            if keyword in message or keyword in subject:
                spam_reasons.append(f"Spam keyword detected: {keyword}")
                break
        
        # Check for excessive capitalization
        if message and len(message) > 20:
            caps_ratio = sum(1 for c in message if c.isupper()) / len(message)
            if caps_ratio > 0.5:
                spam_reasons.append("Excessive capitalization")
        
        # Check for repeated characters
        if re.search(r'(.)\1{5,}', message):
            spam_reasons.append("Suspicious repeated characters")
        
        return len(spam_reasons) > 0, spam_reasons
    
    @staticmethod
    def validate_ticket_id(ticket_id: str) -> bool:
        pattern = r'^TKT-\d{8}-[A-Z0-9]{8}$'
        return bool(re.match(pattern, ticket_id))
    
    @staticmethod
    def validate_session_id(session_id: str) -> bool:
        pattern = r'^CHAT-\d{14}-[A-Z0-9]{8}$'
        return bool(re.match(pattern, session_id))
    
    @staticmethod
    def rate_limit_key(identifier: str, action: str) -> str:
        return f"rate_limit:{action}:{identifier}"