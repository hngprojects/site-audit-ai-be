"""
Test configuration and fixtures for the Site Audit AI API.

This module provides the necessary fixtures and configuration for running tests
with proper database isolation and environment setup.
"""

import os
from typing import Generator
import asyncio

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

import pytest
from fastapi.testclient import TestClient


load_dotenv()

test_db_url = os.getenv("TEST_DATABASE_URL")
if test_db_url:
    if "postgresql://" in test_db_url and "asyncpg" not in test_db_url:
        test_db_url = test_db_url.replace("postgresql://", "postgresql+asyncpg://")
    os.environ["DATABASE_URL"] = test_db_url
else:
    import tempfile

    test_db_path = tempfile.mktemp(suffix=".db")
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{test_db_path}"

@pytest.fixture(scope="session")
def test_app():
    """Create FastAPI test application."""
    from app.main import app

    return app


@pytest.fixture(scope="function")
def client(test_app) -> Generator[TestClient, None, None]:
    """
    Create a test client for making HTTP requests.
    This fixture provides a clean TestClient instance for each test function,
    ensuring proper isolation between tests.
    """
    with TestClient(test_app) as test_client:
        yield test_client
