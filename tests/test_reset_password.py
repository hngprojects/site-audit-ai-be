"""
Test Reset Password Endpoint
"""
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
import asyncio
from app.platform.db.session import get_db
from sqlalchemy import text


@pytest.fixture
def client():
    """Test client fixture"""
    return TestClient(app)


@pytest.fixture
async def reset_token():
    """Get a valid reset token from the database"""
    async for db in get_db():
        result = await db.execute(text('SELECT password_reset_token FROM users WHERE email = :email'), {'email': 'test@example.com'})
        row = result.fetchone()
        return row[0] if row else None


def test_reset_password_valid_token(client, reset_token):
    """Test reset password with valid token"""
    if not reset_token:
        pytest.skip("No reset token available - run forget password test first")

    response = client.post('/auth/reset-password', json={
        'email': 'test@example.com',
        'token': reset_token,
        'new_password': 'NewSecurePass123'
    })

    assert response.status_code == 200
    assert response.json()['success'] == True
    assert 'Password reset successfully' in response.json()['message']


def test_reset_password_invalid_token(client):
    """Test reset password with invalid token"""
    response = client.post('/auth/reset-password', json={
        'email': 'test@example.com',
        'token': 'invalid-token-123',
        'new_password': 'NewSecurePass123'
    })

    assert response.status_code == 400
    assert 'Invalid or expired reset token' in str(response.json())


def test_reset_password_nonexistent_user(client):
    """Test reset password with non-existent user"""
    response = client.post('/auth/reset-password', json={
        'email': 'nonexistent@example.com',
        'token': 'some-token',
        'new_password': 'NewSecurePass123'
    })

    assert response.status_code == 404
    assert 'User not found' in str(response.json())


def test_reset_password_weak_password(client):
    """Test reset password with weak password (validation error)"""
    response = client.post('/auth/reset-password', json={
        'email': 'test@example.com',
        'token': 'some-token',
        'new_password': 'weak'
    })

    # Should fail password validation
    assert response.status_code == 422  # Validation error