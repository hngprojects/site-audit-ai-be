import pytest
from unittest.mock import MagicMock, patch
import sys
import types

# Mock selenium and webdriver_manager modules before import
module_mock = MagicMock()
sys.modules["selenium"] = module_mock
sys.modules["selenium.webdriver"] = module_mock
sys.modules["selenium.webdriver.chrome"] = module_mock
sys.modules["selenium.webdriver.chrome.options"] = module_mock
sys.modules["selenium.webdriver.chrome.service"] = module_mock
sys.modules["webdriver_manager"] = module_mock
sys.modules["webdriver_manager.chrome"] = module_mock

from app.features.scraping.services.selenium_service import SeleniumService

@pytest.fixture
def mock_driver():
    with patch("app.features.scraping.services.selenium_service.webdriver.Chrome") as mock_chrome:
        driver = MagicMock()
        mock_chrome.return_value = driver
        yield driver

@pytest.fixture
def mock_service_class():
    with patch("app.features.scraping.services.selenium_service.Service") as mock_service:
        yield mock_service

@pytest.fixture
def mock_chrome_driver_manager():
    with patch("app.features.scraping.services.selenium_service.ChromeDriverManager") as mock_manager:
        yield mock_manager

def test_scrape_url_success(mock_driver, mock_service_class, mock_chrome_driver_manager):
    # Setup mock
    mock_driver.title = "Example Domain"
    mock_element = MagicMock()
    mock_element.text = "This is an example domain."
    mock_driver.find_element.return_value = mock_element
    
    service = SeleniumService()
    result = service.scrape_url("https://example.com")
    
    assert result["url"] == "https://example.com"
    assert result["title"] == "Example Domain"
    assert result["content_preview"] == "This is an example domain."
    
    mock_driver.get.assert_called_with("https://example.com")
    mock_driver.quit.assert_called_once()

def test_scrape_url_failure(mock_driver, mock_service_class, mock_chrome_driver_manager):
    # Setup mock to raise exception
    mock_driver.get.side_effect = Exception("Connection failed")
    
    service = SeleniumService()
    
    with pytest.raises(Exception) as excinfo:
        service.scrape_url("https://example.com")
    
    assert "Connection failed" in str(excinfo.value)
    mock_driver.quit.assert_called_once()
