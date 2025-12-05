"""
Test URL Discovery Feature

Tests for the new /scan/discovery/discover-urls endpoint
"""
from unittest.mock import patch, MagicMock

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
    
    @patch('app.features.scan.routes.discovery.PageDiscoveryService')
    def test_discover_urls_works_without_authentication(self, mock_service_class, client):
        """Test that endpoint works without authentication (optional auth)"""
        # Create mock instance
        mock_service_instance = MagicMock()
        mock_service_class.return_value = mock_service_instance
        
        # Mock page discovery - return some URLs
        mock_service_instance.discover_pages.return_value = [
            "https://example.com",
            "https://example.com/about",
            "https://example.com/contact"
        ]
        
        # Mock LLM ranking (static method)
        mock_service_class.rank_and_annotate_pages.return_value = [
            {
                "title": "Home",
                "url": "https://example.com",
                "priority": "High Priority",
                "description": "Main landing page"
            },
            {
                "title": "About",
                "url": "https://example.com/about",
                "priority": "Medium Priority",
                "description": "About page"
            }
        ]
        
        response = client.post(
            "/api/v1/scan/discovery/discover-urls",
            json={"url": "https://example.com"}
        )
        
        # Should return 200 without auth token (auth is optional)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "important_urls" in data["data"]
        assert len(data["data"]["important_urls"]) > 0
        mock_service_instance.discover_pages.assert_called_once_with(url="https://example.com", max_pages=15)
        mock_service_class.rank_and_annotate_pages.assert_called_once()
    
    def test_discover_urls_validates_url_format(self, client):
        """Test that endpoint validates URL format"""
        response = client.post(
            "/api/v1/scan/discovery/discover-urls",
            json={"url": "not-a-valid-url"}
        )
        
        # Should return 400 or 422 for invalid URL format
        assert response.status_code in [400, 422]
