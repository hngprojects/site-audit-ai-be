"""
Test URL Discovery Feature

Tests for the new /scan/discovery/discover-urls endpoint
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi import HTTPException

from app.features.scan.services.discovery.page_discovery import PageDiscoveryService


class TestPageDiscoveryService:
    """Tests for enhanced PageDiscoveryService"""
    
    def test_is_same_domain_valid_same_domain(self):
        """Test same domain validation with matching domains"""
        base_domain = "https://example.com"
        url = "https://example.com/about"
        
        result = PageDiscoveryService._is_same_domain(url, base_domain)
        assert result is True
    
    def test_is_same_domain_different_domain(self):
        """Test same domain validation with different domains"""
        base_domain = "https://example.com"
        url = "https://different.com/page"
        
        result = PageDiscoveryService._is_same_domain(url, base_domain)
        assert result is False
    
    def test_is_same_domain_subdomain(self):
        """Test same domain validation with subdomain"""
        base_domain = "https://example.com"
        url = "https://sub.example.com/page"
        
        result = PageDiscoveryService._is_same_domain(url, base_domain)
        assert result is False  # Different subdomain
    
    def test_is_same_domain_different_scheme(self):
        """Test same domain validation with different scheme"""
        base_domain = "https://example.com"
        url = "http://example.com/page"
        
        result = PageDiscoveryService._is_same_domain(url, base_domain)
        assert result is False  # Different scheme
    
    def test_is_same_domain_invalid_url(self):
        """Test same domain validation with invalid URL"""
        base_domain = "https://example.com"
        url = "not-a-valid-url"
        
        result = PageDiscoveryService._is_same_domain(url, base_domain)
        assert result is False
    
    def test_is_same_domain_no_scheme(self):
        """Test same domain validation with URL missing scheme"""
        base_domain = "https://example.com"
        url = "//example.com/page"
        
        result = PageDiscoveryService._is_same_domain(url, base_domain)
        assert result is False  # No scheme
    
    @patch('app.features.scan.services.discovery.page_discovery.webdriver.Chrome')
    def test_discover_pages_returns_list(self, mock_chrome):
        """Test that discover_pages returns a list of URLs"""
        # Mock the webdriver
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver
        
        # Mock the page load
        mock_driver.get.return_value = None
        
        # Mock link elements
        mock_link = MagicMock()
        mock_link.get_attribute.return_value = "https://example.com/about"
        mock_driver.find_elements.return_value = [mock_link]
        
        result = PageDiscoveryService.discover_pages("https://example.com", max_pages=2)
        
        assert isinstance(result, list)
        assert len(result) <= 2
        mock_driver.quit.assert_called_once()


class TestDiscoverUrlsEndpoint:
    """Integration tests for the discover-urls endpoint"""

    @patch('app.features.scan.routes.discovery.PageDiscoveryService._fallback_selection')
    @patch('app.features.scan.routes.discovery.PageDiscoveryService.discover_pages')
    def test_discover_urls_works_without_authentication(
        self,
        mock_discover_pages,
        mock_fallback_selection,
        client
    ):
        """
        Test that endpoint works without authentication (auth is optional)
        and correctly calls the discovery + ranking services.
        """
        # Mock page discovery - return some URLs
        mock_discover_pages.return_value = [
            "https://example.com",
            "https://example.com/about",
            "https://example.com/contact",
        ]
        
        mock_fallback_selection.return_value = [
            {
                "title": "Home",
                "url": "https://example.com",
                "priority": "high",
                "description": "Main landing page",
            },
            {
                "title": "About",
                "url": "https://example.com/about",
                "priority": "medium",
                "description": "About page",
            },
        ]
        
        response = client.post(
            "/api/v1/scan/discovery/discover-urls",
            json={"url": "https://example.com"},
        )
        
        # Endpoint should work without auth token
        assert response.status_code == 200
        data = response.json()
        
        # api_response wrapper
        assert data["status"] == "success"
        assert "data" in data
        assert "important_urls" in data["data"]
        assert len(data["data"]["important_urls"]) > 0

        # Verify discover_pages was called once with correct arguments
        mock_discover_pages.assert_called_once()
        called_kwargs = mock_discover_pages.call_args.kwargs
        # Be robust to trailing slash differences
        assert called_kwargs["max_pages"] == 10
        assert called_kwargs["url"].rstrip("/") == "https://example.com"

        # Verify fallback selection was called with discovered pages
        mock_fallback_selection.assert_called_once()
        fallback_kwargs = mock_fallback_selection.call_args.kwargs
        assert fallback_kwargs["pages"] == mock_discover_pages.return_value
        assert fallback_kwargs["max_pages"] == 10
    
    def test_discover_urls_validates_url_format(self, client):
        """Test that endpoint validates URL format"""
        response = client.post(
            "/api/v1/scan/discovery/discover-urls",
            json={"url": "not-a-valid-url"},
        )
        
        # Should return 400 or 422 for invalid URL format
        assert response.status_code in [400, 422]
