from typing import Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.common.exceptions import TimeoutException, WebDriverException


class PageLoaderService:
    """Service for loading web pages using Selenium WebDriver"""
    
    @staticmethod
    def _create_driver() -> WebDriver:
        """
        Create and configure a Chrome WebDriver instance.
        Reuses the pattern from page_discovery/services/discovery_service.py
        
        Returns:
            WebDriver: Configured Chrome driver
        """
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(30)  # 30 second timeout
        
        return driver
    
    @staticmethod
    def load_page(url: str) -> WebDriver:
        """
        Load a web page and return the driver.
        
        IMPORTANT: Caller MUST call driver.quit() when done!
        
        Args:
            url: The URL to load
            
        Returns:
            WebDriver: Driver with the page loaded
            
        Raises:
            TimeoutException: If page takes longer than 30 seconds to load
            WebDriverException: If there's an issue with the driver
            Exception: For any other errors during page load
            
        Example:
            driver = PageLoaderService.load_page("https://example.com")
            try:
                # Do something with driver
                metadata = ExtractorService.extract_metadata(driver)
            finally:
                driver.quit()  # Always cleanup!
        """
        driver = PageLoaderService._create_driver()
        
        try:
            driver.get(url)
            return driver
        except TimeoutException:
            driver.quit()
            raise TimeoutException(f"Page load timeout after 30 seconds for URL: {url}")
        except WebDriverException as e:
            driver.quit()
            raise WebDriverException(f"WebDriver error loading URL {url}: {str(e)}")
        except Exception as e:
            driver.quit()
            raise Exception(f"Unexpected error loading URL {url}: {str(e)}")