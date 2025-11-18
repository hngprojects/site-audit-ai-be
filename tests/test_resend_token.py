"""
Test Resend Reset Token Endpoint
"""
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Test client fixture"""
    return TestClient(app)


def test_resend_reset_token_existing_user(client):
    """Test resend reset token with existing user"""
    with patch('app.platform.services.email.send_email') as mock_send:
        mock_send.return_value = None

        response = client.post('/auth/resend-reset-token', json={'email': 'test@example.com'})

        assert response.status_code == 200
        assert response.json()['success'] == True
        assert 'New password reset email sent' in response.json()['message']
        assert '1 minute' in response.json()['message']
        assert mock_send.called


def test_resend_reset_token_nonexistent_user(client):
    """Test resend reset token with non-existent user"""
    with patch('app.platform.services.email.send_email') as mock_send:
        mock_send.return_value = None

        response = client.post('/auth/resend-reset-token', json={'email': 'nonexistent@example.com'})

        assert response.status_code == 404
        assert 'User not found' in str(response.json())
        assert not mock_send.called  # Email should not be sent


def test_resend_reset_token_invalid_email_format(client):
    """Test resend reset token with invalid email format"""
    response = client.post('/auth/resend-reset-token', json={'email': 'invalid-email'})

    # Pydantic should validate email format
    assert response.status_code == 422  # Validation error