import bcrypt
from datetime import datetime, timedelta
from typing import Optional
import secrets
import jwt
import os
import hashlib

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 hours
# Refresh token expiry (e.g., 7 days)
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))


def hash_password(password: str) -> str:
    password_hash = hashlib.sha256(password.encode('utf-8')).digest()
    
    # Generate salt and hash with bcrypt
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_hash, salt)
    
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    Uses SHA-256 pre-hashing to match the hashing method.
    """
    # Pre-hash with SHA-256 to match the hashing method
    password_hash = hashlib.sha256(plain_password.encode('utf-8')).digest()
    
    # Verify with bcrypt
    return bcrypt.checkpw(password_hash, hashed_password.encode('utf-8'))



def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT refresh token (longer expiry)"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "iat": datetime.utcnow(), "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt



def decode_access_token(token: str) -> dict:
    """Decode and verify a JWT access token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.JWTError:
        raise ValueError("Invalid token")

def decode_refresh_token(token: str) -> dict:
    """Decode and verify a JWT refresh token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            raise ValueError("Not a refresh token")
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Refresh token has expired")
    except jwt.JWTError:
        raise ValueError("Invalid refresh token")


def generate_verification_token() -> str:
    """Generate a secure random token for email verification or password reset"""
    return secrets.token_urlsafe(32)


def generate_otp() -> str:
    """Generate a 6-digit OTP for email verification"""
    return ''.join([str(secrets.randbelow(10)) for _ in range(6)])
