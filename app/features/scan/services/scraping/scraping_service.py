from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from typing import Dict, Any
import tempfile
import os
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
            
            # Wait for JavaScript to render content
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.common.by import By
            
            # Wait for document.readyState to be complete
            WebDriverWait(driver, timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            
            # Wait for body to have content (handling SPAs)
            try:
                WebDriverWait(driver, timeout).until(
                    lambda d: len(d.find_element(By.TAG_NAME, "body").text.strip()) > 0
                )
            except:
                # If body is empty, check for common main content containers
                try:
                    WebDriverWait(driver, timeout).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "main, article, #app, #root, .content"))
                    )
                except:
                    pass # Proceed even if specific content isn't found, we tried our best
            
            return driver  # caller is responsible for driver.quit()
        except (TimeoutException, WebDriverException):
            driver.quit()
            raise
    
    
    @staticmethod
    def scrape_page(url: str, timeout: int = 5) -> Dict[str, Any]:
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