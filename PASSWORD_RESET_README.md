# Password Reset System Documentation

## Overview

This is a production-ready password reset system for FastAPI with the following features:

- Secure token-based password reset (NO OTP)
- Email notifications via SendGrid
- 30-minute token expiration
- Async SQLAlchemy with PostgreSQL
- Bcrypt password hashing
- Clean, modular architecture

## Tech Stack

- **FastAPI** - Modern web framework
- **PostgreSQL** - Database with asyncpg driver
- **SQLAlchemy** - Async ORM
- **Passlib (bcrypt)** - Password hashing
- **SendGrid** - Email delivery
- **Python secrets** - Secure token generation

## Project Structure

```
app/
├── features/
│   └── auth/
│       ├── __init__.py
│       ├── endpoints.py              # API endpoints
│       ├── models/
│       │   ├── __init__.py
│       │   └── user.py               # User model with reset fields
│       ├── schemas/
│       │   ├── __init__.py
│       │   └── password_reset.py     # Pydantic schemas
│       ├── services/
│       │   ├── __init__.py
│       │   └── password_reset.py     # Business logic
│       └── utils/
│           ├── __init__.py
│           ├── emailer.py            # SendGrid email functions
│           └── password.py           # Password hashing utilities
├── platform/
│   ├── config.py                     # Configuration
│   └── db/
│       └── session.py                # Database session
└── main.py                           # FastAPI app with routes
```

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and update:

```bash
# Database (use asyncpg driver)
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/your_db

# SendGrid API Key
SENDGRID_API_KEY=SG.your-api-key-here

# Frontend URL for reset links
FRONTEND_URL=https://yourdomain.com

# Email Configuration
MAIL_FROM_ADDRESS=noreply@yourdomain.com
MAIL_FROM_NAME="Your App Name"
```

### 3. Create Database Tables

Run the migration script:

```bash
python scripts/create_user_table.py
```

Or use Alembic for production:

```bash
alembic revision --autogenerate -m "Add users table"
alembic upgrade head
```

### 4. Start the Server

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

## API Endpoints

### 1. Request Password Reset

**POST** `/auth/request-password-reset`

Request a password reset link to be sent via email.

**Request Body:**
```json
{
  "email": "user@example.com"
}
```

**Response (200 OK):**
```json
{
  "message": "If this email exists, a password reset link has been sent."
}
```

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/auth/request-password-reset" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com"}'
```

### 2. Reset Password

**POST** `/auth/reset-password`

Reset the password using a valid reset token.

**Request Body:**
```json
{
  "token": "secure-reset-token-from-email",
  "new_password": "NewSecurePassword123!"
}
```

**Response (200 OK):**
```json
{
  "message": "Password has been reset successfully."
}
```

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/auth/reset-password" \
  -H "Content-Type: application/json" \
  -d '{
    "token": "abc123...",
    "new_password": "NewPassword123!"
  }'
```

## User Model Schema

```python
class User(Base):
    id: int                          # Primary key
    email: str                       # Unique email
    password: str                    # Hashed password
    reset_token: Optional[str]       # Password reset token
    reset_token_expiry: Optional[datetime]  # Token expiration
    created_at: datetime
    updated_at: datetime
```

## Security Features

### 1. Secure Token Generation
- Uses Python's `secrets.token_urlsafe(48)` for cryptographically secure tokens
- Generates 64-character URL-safe tokens

### 2. Token Expiration
- Tokens expire after 30 minutes
- Expired tokens are automatically rejected

### 3. Password Hashing
- Uses bcrypt via Passlib
- Automatically handles salting and iterations

### 4. Email Privacy
- Doesn't reveal if an email exists in the system
- Returns same message for existing and non-existing emails

### 5. Token Cleanup
- Tokens are cleared after successful password reset
- Old tokens become invalid immediately

## Email Templates

The system sends two types of emails:

### 1. Password Reset Email
Sent when user requests password reset:
- Contains reset link with token
- Includes expiration notice (30 minutes)
- Plain text and HTML versions

### 2. Confirmation Email
Sent after successful password reset:
- Confirms password was changed
- Security notice to contact support if unauthorized

## Error Handling

The API returns appropriate HTTP status codes:

- **200 OK** - Success
- **400 Bad Request** - Invalid/expired token
- **404 Not Found** - User not found (security message)
- **500 Internal Server Error** - Server error

## Testing

### Manual Testing with cURL

1. **Create a test user** (you'll need to create a registration endpoint or manually insert):
```sql
INSERT INTO users (email, password) 
VALUES ('test@example.com', '$2b$12$...');  -- Use hashed password
```

2. **Request password reset:**
```bash
curl -X POST "http://localhost:8000/auth/request-password-reset" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}'
```

3. **Check email for token**, then reset password:
```bash
curl -X POST "http://localhost:8000/auth/reset-password" \
  -H "Content-Type: application/json" \
  -d '{
    "token": "TOKEN_FROM_EMAIL",
    "new_password": "NewPassword123!"
  }'
```

### Unit Tests

Create tests using pytest:

```python
# tests/test_password_reset.py
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_request_password_reset():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/auth/request-password-reset",
            json={"email": "test@example.com"}
        )
        assert response.status_code == 200
```

## SendGrid Setup

### 1. Create SendGrid Account
- Sign up at https://sendgrid.com
- Verify your sender identity
- Create an API key

### 2. Get API Key
1. Go to Settings → API Keys
2. Click "Create API Key"
3. Select "Full Access" or "Restricted Access" with Mail Send permissions
4. Copy the API key and add to `.env`

### 3. Verify Sender
1. Go to Settings → Sender Authentication
2. Verify your domain or single sender email
3. Update `MAIL_FROM_ADDRESS` in `.env`

## Production Considerations

### 1. Environment Variables
- Never commit `.env` file
- Use secure secret management (AWS Secrets Manager, Azure Key Vault, etc.)

### 2. Database
- Use connection pooling
- Set appropriate pool size in SQLAlchemy
- Enable SSL for database connections

### 3. Email Rate Limiting
- Implement rate limiting for password reset requests
- Prevent email bombing attacks

### 4. Token Security
- Consider adding user agent/IP validation
- Implement maximum reset attempts

### 5. Logging
- Log all password reset attempts
- Monitor for suspicious patterns
- Use structured logging

### 6. CORS Configuration
- Configure CORS properly for your frontend domain
- Restrict allowed origins in production

## Customization

### Change Token Expiration Time

In `app/features/auth/services/password_reset.py`:

```python
# Change from 30 minutes to 1 hour
reset_token_expiry = datetime.utcnow() + timedelta(hours=1)
```

### Customize Email Template

Edit `app/features/auth/utils/emailer.py`:

```python
html_content = f"""
<html>
  <body>
    <!-- Your custom HTML template -->
  </body>
</html>
"""
```

### Change Password Requirements

Edit `app/features/auth/schemas/password_reset.py`:

```python
new_password: str = Field(
    ...,
    min_length=12,  # Increase minimum length
    max_length=128,
    regex=r"^(?=.*[A-Z])(?=.*[a-z])(?=.*\d).*$"  # Add complexity rules
)
```

## Troubleshooting

### Issue: SendGrid emails not sending

**Solution:**
1. Verify API key is correct
2. Check sender email is verified in SendGrid
3. Review SendGrid logs in dashboard
4. Check application logs for errors

### Issue: Token expired immediately

**Solution:**
1. Check server time is correct
2. Ensure timezone is UTC
3. Verify database timezone settings

### Issue: Database connection errors

**Solution:**
1. Verify `DATABASE_URL` format: `postgresql+asyncpg://...`
2. Check PostgreSQL is running
3. Verify credentials and database exists
4. Ensure `asyncpg` is installed

## Support

For issues or questions:
- Check FastAPI docs: https://fastapi.tiangolo.com
- SendGrid docs: https://docs.sendgrid.com
- SQLAlchemy async docs: https://docs.sqlalchemy.org/en/14/orm/extensions/asyncio.html

## License

[Your License Here]
