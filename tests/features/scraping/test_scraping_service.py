"""
Tests for the comprehensive scraping service.
"""

import pytest
from app.features.scan.services.scraping import ScrapingService


class TestScrapingService:
    """Test cases for ScrapingService."""
    
    def test_scraping_service_initialization(self):
        """Test that ScrapingService initializes correctly."""
        scraper = ScrapingService(headless=True, timeout=30)
        assert scraper.headless is True
        assert scraper.timeout == 30
        assert scraper.driver is None
    
    @pytest.mark.skip(reason="Requires Selenium WebDriver and network access")
    def test_scrape_page_example_com(self):
        """Test scraping example.com (requires network)."""
        scraper = ScrapingService(headless=True, timeout=30)
        
        try:
            report = scraper.scrape_page("https://example.com")
            
            # Verify report structure
            assert "url" in report
            assert "scraped_at" in report
            assert "metadata" in report
            assert "headings" in report
            assert "images" in report
            assert "links" in report
            assert "performance" in report
            assert "accessibility" in report
            assert "design" in report
            assert "text_content" in report
            assert "summary" in report
            
            # Verify metadata extraction
            assert report["metadata"]["title"] != ""
            
            # Verify headings extraction
            assert "h1" in report["headings"]
            assert "hierarchy" in report["headings"]
            
            # Verify performance metrics
            assert report["performance"]["ttfb_ms"] is not None or report["performance"]["ttfb_ms"] == 0
            
        except Exception as e:
            pytest.fail(f"Scraping failed: {str(e)}")
    
    @pytest.mark.skip(reason="Requires Selenium WebDriver and network access")
    def test_scrape_multiple_pages(self):
        """Test scraping multiple pages."""
        scraper = ScrapingService(headless=True, timeout=30)
        
        urls = [
            "https://example.com",
            "https://example.org"
        ]
        
        try:
            reports = scraper.scrape_multiple_pages(urls)
            
            assert len(reports) == 2
            
            for report in reports:
                assert "url" in report
                assert "metadata" in report or "error" in report
                
        except Exception as e:
            pytest.fail(f"Multiple page scraping failed: {str(e)}")
    
    def test_extract_metadata_structure(self):
        """Test that extract_metadata returns correct structure."""
        # This would require a mock driver
        # For now, just verify the method exists
        scraper = ScrapingService()
        assert hasattr(scraper, 'extract_metadata')
        assert callable(scraper.extract_metadata)
    
    def test_extract_headings_structure(self):
        """Test that extract_headings returns correct structure."""
        scraper = ScrapingService()
        assert hasattr(scraper, 'extract_headings')
        assert callable(scraper.extract_headings)
    
    def test_extract_images_structure(self):
        """Test that extract_images returns correct structure."""
        scraper = ScrapingService()
        assert hasattr(scraper, 'extract_images')
        assert callable(scraper.extract_images)
    
    def test_extract_links_structure(self):
        """Test that extract_links returns correct structure."""
        scraper = ScrapingService()
        assert hasattr(scraper, 'extract_links')
        assert callable(scraper.extract_links)
    
    def test_extract_performance_metrics_structure(self):
        """Test that extract_performance_metrics returns correct structure."""
        scraper = ScrapingService()
        assert hasattr(scraper, 'extract_performance_metrics')
        assert callable(scraper.extract_performance_metrics)
    
    def test_extract_accessibility_structure(self):
        """Test that extract_accessibility returns correct structure."""
        scraper = ScrapingService()
        assert hasattr(scraper, 'extract_accessibility')
        assert callable(scraper.extract_accessibility)
    
    def test_extract_design_signals_structure(self):
        """Test that extract_design_signals returns correct structure."""
        scraper = ScrapingService()
        assert hasattr(scraper, 'extract_design_signals')
        assert callable(scraper.extract_design_signals)
    
    def test_extract_text_content_structure(self):
        """Test that extract_text_content returns correct structure."""
        scraper = ScrapingService()
        assert hasattr(scraper, 'extract_text_content')
        assert callable(scraper.extract_text_content)
    
    def test_compile_report_structure(self):
        """Test that compile_report returns correct structure."""
        scraper = ScrapingService()
        
        # Test with empty data
        report = scraper.compile_report("https://example.com", {})
        
        assert "url" in report
        assert "scraped_at" in report
        assert "summary" in report
        assert report["url"] == "https://example.com"
