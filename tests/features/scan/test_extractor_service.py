import pytest
from unittest.mock import MagicMock, patch
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import NoSuchElementException

from app.features.scan.services.extraction.extractor_service import ExtractorService
from app.features.scan.schemas.metadata import MetadataExtractionResult, DescriptionMetadata

class TestExtractorService:
    @pytest.fixture
    def mock_driver(self):
        driver = MagicMock()
        return driver

    @pytest.fixture
    def mock_element(self):
        element = MagicMock(spec=WebElement)
        return element

    def test_extract_headings(self, mock_driver, mock_element):
        # Setup
        mock_element.text = "Test Heading"
        mock_driver.find_elements.return_value = [mock_element]
        
        # Execute
        headings = ExtractorService.extract_headings(mock_driver)
        
        # Verify
        assert "h1" in headings
        assert headings["h1"] == ["Test Heading"]
        assert "h2" in headings
        
    def test_extract_images(self, mock_driver, mock_element):
        # Setup
        mock_element.get_attribute.side_effect = lambda x: "test.jpg" if x == "src" else "Test Alt"
        mock_driver.find_elements.return_value = [mock_element]
        
        # Execute
        images = ExtractorService.extract_images(mock_driver)
        
        # Verify
        assert len(images) == 1
        assert images[0]["src"] == "test.jpg"
        assert images[0]["alt"] == "Test Alt"

    def test_extract_accessibility_missing_alt(self, mock_driver, mock_element):
        # Setup
        mock_element.get_attribute.side_effect = lambda x: "test.jpg" if x == "src" else ""
        mock_driver.find_elements.return_value = [mock_element] # For images
        
        # Execute
        issues = ExtractorService.extract_accessibility(mock_driver)
        
        # Verify
        assert "images_missing_alt" in issues
        assert len(issues["images_missing_alt"]) == 1
        assert issues["images_missing_alt"][0] == "test.jpg"

    def test_extract_metadata_title(self, mock_driver, mock_element):
        # Setup
        mock_element.text = "Test Page Title"
        mock_driver.find_element.return_value = mock_element
        mock_driver.current_url = "https://example.com"
        
        # Execute
        # We need to mock the other internal methods called by extract_metadata
        with patch.object(ExtractorService, '_extract_description') as mock_desc, \
             patch.object(ExtractorService, '_extract_keywords') as mock_kw, \
             patch.object(ExtractorService, '_extract_open_graph') as mock_og, \
             patch.object(ExtractorService, '_extract_canonical_url') as mock_can, \
             patch.object(ExtractorService, '_extract_viewport') as mock_view:
            
            # Setup mocks
            mock_desc.return_value = DescriptionMetadata(value="Test Description", issues=[], is_valid=True, length=16)
            mock_kw.return_value = "test, keywords"
            mock_og.return_value = None
            mock_can.return_value = None
            mock_view.return_value = None
            
            result = ExtractorService.extract_metadata(mock_driver)
            
            # Verify
            assert isinstance(result, MetadataExtractionResult)
            assert result.title.value == "Test Page Title"
            assert result.has_title is True

    def test_extract_text_content(self, mock_driver, mock_element):
        # Setup
        mock_element.text = "This is a test sentence. This is another test sentence."
        mock_driver.find_element.return_value = mock_element
        mock_driver.find_elements.return_value = [] # For headers
        
        # Execute
        content = ExtractorService.extract_text_content(mock_driver)
        
        # Verify
        assert content["word_count"] == 10
        assert content["readability_score"] > 0
