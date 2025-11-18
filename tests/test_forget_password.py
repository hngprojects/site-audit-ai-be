"""
Test Forget Password Endpoint
"""
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Test client fixture"""
    return TestClient(app)


def test_forget_password_existing_user(client):
    """Test forget password with existing user (user created in previous tests)"""
    with patch('app.platform.services.email.send_email') as mock_send:
        mock_send.return_value = None

        response = client.post('/auth/forgot-password', json={'email': 'test@example.com'})

        assert response.status_code == 200
        assert response.json()['success'] == True
        assert 'Password reset email sent' in response.json()['message']
        assert '1 minute' in response.json()['message']
        assert mock_send.called


def test_forget_password_nonexistent_user(client):
    """Test forget password with non-existent user"""
    with patch('app.platform.services.email.send_email') as mock_send:
        mock_send.return_value = None

        response = client.post('/auth/forgot-password', json={'email': 'nonexistent@example.com'})

        assert response.status_code == 404
        assert 'User not found' in str(response.json())
        assert not mock_send.called  # Email should not be sent


def test_forget_password_invalid_email_format(client):
    """Test forget password with invalid email format"""
    response = client.post('/auth/forgot-password', json={'email': 'invalid-email'})

    # Pydantic should validate email format
    assert response.status_code == 422 