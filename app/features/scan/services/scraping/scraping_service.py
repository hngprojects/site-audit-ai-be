from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from typing import Dict, Any
import tempfile
import os

# Cache ChromeDriver path to avoid repeated downloads
_CHROMEDRIVER_PATH = None


class ScrapingService:
    @staticmethod
    def build_driver() -> webdriver.Chrome:
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # Headless mode
        chrome_options.add_argument('--no-sandbox')
        driver_service = Service(executable_path='/usr/local/bin/chromedriver')  
        driver = webdriver.Chrome(service=driver_service, options=chrome_options) 

        return driver


    @staticmethod
    def load_page(url: str, timeout: int = 10) -> webdriver.Chrome:
        """
        Load a page and return the WebDriver instance.
        Caller is responsible for calling driver.quit().
        """
        driver = ScrapingService.build_driver()
        driver.set_page_load_timeout(timeout)
        try:
            driver.get(url)
            return driver  # caller is responsible for driver.quit()
        except (TimeoutException, WebDriverException):
            driver.quit()
            raise
    
    
    @staticmethod
    def scrape_page(url: str, timeout: int = 15) -> Dict[str, Any]:
        """
        Scrape a page and return serializable data (for Celery tasks).
        Driver is automatically closed after scraping.
        
        Args:
            url: URL to scrape
            timeout: Page load timeout in seconds
            
        Returns:
            Dict with HTML content and metadata (fully serializable)
        """
        driver = None
        try:
            driver = ScrapingService.load_page(url, timeout)
            
            # Extract all data we need
            html_content = driver.page_source
            page_title = driver.title or None
            current_url = driver.current_url
            
            return {
                "url": url,
                "current_url": current_url,  # Final URL after redirects
                "html": html_content,
                "page_title": page_title,
                "content_length": len(html_content),
                "success": True
            }
            
        except TimeoutException as e:
            return {
                "url": url,
                "html": None,
                "page_title": None,
                "error": f"Timeout loading page: {str(e)}",
                "success": False
            }
        except WebDriverException as e:
            return {
                "url": url,
                "html": None,
                "page_title": None,
                "error": f"WebDriver error: {str(e)}",
                "success": False
            }
        except Exception as e:
            return {
                "url": url,
                "html": None,
                "page_title": None,
                "error": f"Unexpected error: {str(e)}",
                "success": False
            }
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass  # Ignore cleanup errors