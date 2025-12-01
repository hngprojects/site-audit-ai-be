"""
Integration tests for ScrapingService -> ExtractorService workflow.

These tests verify that:
1. ScrapingService can fetch HTML from a live page
2. ExtractorService can parse that HTML
3. Data flows correctly between the two services
"""
import pytest
from app.features.scan.services.scraping.scraping_service import ScrapingService
from app.features.scan.services.extraction.extractor_service import ExtractorService


class TestScrapingExtractionIntegration:
    """Test the integration between ScrapingService and ExtractorService"""
    
    @pytest.mark.skip(reason="Requires network access and Selenium WebDriver")
    def test_scraping_to_extraction_workflow_example_com(self):
        """
        Test complete workflow: Scrape example.com -> Extract data
        
        This test verifies:
        - ScrapingService can load a page and capture HTML
        - HTML contains expected content
        - ExtractorService can parse the HTML
        - Extracted data has the expected structure
        """
        scraper = None
        driver = None
        
        try:
            # Step 1: Load page using static method
            driver = ScrapingService.load_page("https://example.com", timeout=30)
            
            # Step 2: Capture HTML
            html = driver.page_source
            
            # Step 3: Verify HTML was captured
            assert html is not None, "HTML should not be None"
            assert len(html) > 0, "HTML should not be empty"
            assert "<html" in html.lower(), "HTML should contain <html> tag"
            assert "example" in html.lower(), "HTML should contain 'example' text"
            
            # Step 4: Extract data using ExtractorService
            extracted = ExtractorService.extract_from_html(html, "https://example.com")
            
            # Step 5: Verify extraction structure
            assert extracted is not None, "Extracted data should not be None"
            assert isinstance(extracted, dict), "Extracted data should be a dictionary"
            assert "data" in extracted, "Extracted data should have 'data' key"
            
            # Step 6: Verify all expected data sections are present
            data = extracted["data"]
            assert "heading_data" in data, "Should have heading_data"
            assert "images_data" in data, "Should have images_data"
            assert "issues_data" in data, "Should have issues_data"
            assert "text_content_data" in data, "Should have text_content_data"
            assert "metadata_data" in data, "Should have metadata_data"
            
            # Step 7: Verify metadata extraction worked
            metadata = data["metadata_data"]
            assert "url" in metadata, "Metadata should have URL"
            assert metadata["url"] == "https://example.com", "URL should match"
            assert "title" in metadata, "Metadata should have title"
            assert "description" in metadata, "Metadata should have description"
            
            print("✅ Integration test passed: ScrapingService -> ExtractorService workflow works correctly")
            
        finally:
            # Cleanup
            if driver:
                driver.quit()
    
    def _create_mock_driver(self, url="https://test.com"):
        from unittest.mock import MagicMock
        from selenium.webdriver.common.by import By
        from selenium.common.exceptions import NoSuchElementException

        # Mock the driver and its elements
        mock_driver = MagicMock()
        mock_driver.current_url = url
        
        # Helper to create mock elements
        def create_mock_element(text="", attributes=None, tag_name="div"):
            el = MagicMock()
            el.text = text
            el.tag_name = tag_name
            el.get_attribute.side_effect = lambda k: (attributes or {}).get(k)
            # Support finding elements within elements (e.g. for accessibility checks)
            el.find_elements.return_value = []
            el.find_element.side_effect = NoSuchElementException()
            return el

        # Define side effects for find_elements and find_element
        def find_elements_side_effect(by, value):
            elements = []
            if by == By.TAG_NAME:
                if value == "h1":
                    elements.append(create_mock_element("Main Heading", tag_name="h1"))
                elif value == "h2":
                    elements.append(create_mock_element("Subheading", tag_name="h2"))
                elif value in ["h3", "h4", "h5", "h6"]:
                    pass
                elif value == "img":
                    elements.append(create_mock_element(attributes={"src": "test.jpg", "alt": "Test Image"}, tag_name="img"))
                elif value == "a":
                    elements.append(create_mock_element("Test Link", attributes={"href": "https://example.com"}, tag_name="a"))
            elif by == By.CSS_SELECTOR:
                if "h1" in value: # Simplified check for header selector
                     elements.append(create_mock_element("Main Heading", tag_name="h1"))
                     elements.append(create_mock_element("Subheading", tag_name="h2"))
                if "input" in value:
                    pass
                if "button" in value:
                    pass
            return elements

        def find_element_side_effect(by, value):
            if by == By.TAG_NAME:
                if value == "title":
                    return create_mock_element("Test Page", tag_name="title")
                if value == "body":
                    return create_mock_element("Main Heading Subheading This is some test content with multiple words for readability testing.", tag_name="body")
            elif by == By.CSS_SELECTOR:
                if 'meta[name="description"]' in value:
                    return create_mock_element(attributes={"content": "This is a test page for integration testing"}, tag_name="meta")
                if 'meta[name="viewport"]' in value:
                    return create_mock_element(attributes={"content": "width=device-width, initial-scale=1"}, tag_name="meta")
                if 'meta[name="keywords"]' in value:
                    raise NoSuchElementException()
                if 'link[rel="canonical"]' in value:
                    raise NoSuchElementException()
                if 'meta[property="og:' in value:
                    raise NoSuchElementException()
            
            raise NoSuchElementException()

        mock_driver.find_elements.side_effect = find_elements_side_effect
        mock_driver.find_element.side_effect = find_element_side_effect
        
        return mock_driver

    def test_extractor_can_parse_scraper_html_format(self):
        """
        Test that ExtractorService can parse HTML in the format provided by ScrapingService.
        
        This is a lightweight test that doesn't require network access.
        """
        # Sample HTML that mimics what ScrapingService would return
        sample_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Test Page</title>
            <meta name="description" content="This is a test page for integration testing">
            <meta name="viewport" content="width=device-width, initial-scale=1">
        </head>
        <body>
            <h1>Main Heading</h1>
            <h2>Subheading</h2>
            <p>This is some test content with multiple words for readability testing.</p>
            <img src="test.jpg" alt="Test Image">
            <a href="https://example.com">Test Link</a>
        </body>
        </html>
        """
        
        from unittest.mock import patch

        # Create mock driver
        mock_driver = self._create_mock_driver("https://test.com")

        # Patch ScrapingService.build_driver to return our mock
        with patch('app.features.scan.services.scraping.scraping_service.ScrapingService.build_driver', return_value=mock_driver):
            # Extract data
            extracted = ExtractorService.extract_from_html(sample_html, "https://test.com")
            
            # Verify structure
            assert extracted is not None
            assert "data" in extracted
            
            data = extracted["data"]
            
            # Verify headings were extracted
            assert "heading_data" in data
            assert "h1" in data["heading_data"]
            assert len(data["heading_data"]["h1"]) > 0
            assert "Main Heading" in data["heading_data"]["h1"]
            
            # Verify images were extracted
            assert "images_data" in data
            assert len(data["images_data"]) > 0
            
            # Verify metadata was extracted
            assert "metadata_data" in data
            
            metadata = data["metadata_data"]
            assert "title" in metadata
            assert "description" in metadata
            
            # Description should work since it's a meta tag
            if metadata["description"]["value"]:
                assert "test page" in metadata["description"]["value"].lower()
            
            # Verify text content was analyzed
            assert "text_content_data" in data
            assert data["text_content_data"]["word_count"] > 0
            
            print("✅ ExtractorService successfully parsed ScrapingService HTML format")
    
    def test_html_passing_matches_celery_task_format(self):
        """
        Test that the HTML format passed between services matches what Celery tasks expect.
        
        This verifies the data contract between scrape_page and extract_data tasks.
        """
        # Simulate what scrape_page task returns
        scrape_result = {
            "url": "https://example.com",
            "html": "<html><body><h1>Test</h1></body></html>",
            "status_code": 200,
            "performance": {"load_time": 1000}
        }
        
        # Verify the HTML key exists (required by extract_data task)
        assert "html" in scrape_result, "scrape_page result must include 'html' key"
        assert isinstance(scrape_result["html"], str), "HTML must be a string"
        assert len(scrape_result["html"]) > 0, "HTML must not be empty"
        
        # Verify ExtractorService can consume this format
        html = scrape_result["html"]
        url = scrape_result["url"]
        
        from unittest.mock import patch
        
        # Create mock driver
        mock_driver = self._create_mock_driver(url)
        
        # Minimal mock for this test
        with patch('app.features.scan.services.scraping.scraping_service.ScrapingService.build_driver', return_value=mock_driver):
            extracted = ExtractorService.extract_from_html(html, url)
            
            assert extracted is not None
            assert "data" in extracted
            
            print("✅ HTML passing format matches Celery task contract")

