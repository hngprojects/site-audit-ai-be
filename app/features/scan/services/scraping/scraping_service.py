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
        
        # Create temp directory for Chrome user data to avoid DevToolsActivePort issues
        temp_dir = tempfile.mkdtemp()
        
        # CRITICAL: These flags fix "Chrome failed to start" on Linux servers
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-setuid-sandbox")
        
        # Fix DevToolsActivePort file doesn't exist error
        chrome_options.add_argument("--remote-debugging-pipe")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-background-networking")
        
        # Crash prevention flags
        chrome_options.add_argument("--disable-crash-reporter")
        chrome_options.add_argument("--disable-in-process-stack-traces")
        chrome_options.add_argument("--disable-logging")
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_argument("--output=/dev/null")
        
        # Use temp directory for user data (prevents profile lock issues)
        chrome_options.add_argument(f"--user-data-dir={temp_dir}")
        chrome_options.add_argument(f"--data-path={os.path.join(temp_dir, 'data')}")
        chrome_options.add_argument(f"--disk-cache-dir={os.path.join(temp_dir, 'cache')}")
        
        # Additional stability options
        chrome_options.add_argument("--disable-software-rasterizer")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--disable-dev-tools")
        chrome_options.add_argument("--no-first-run")
        chrome_options.add_argument("--no-zygote")
        chrome_options.add_argument("--single-process")
        chrome_options.add_argument("--disable-default-apps")
        chrome_options.add_argument("--disable-sync")
        chrome_options.add_argument("--disable-translate")
        chrome_options.add_argument("--mute-audio")
        chrome_options.add_argument("--hide-scrollbars")
        chrome_options.add_argument("--metrics-recording-only")
        chrome_options.add_argument("--safebrowsing-disable-auto-update")
        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # Page load strategy
        chrome_options.set_capability("pageLoadStrategy", "eager")

        # Use webdriver-manager with caching to avoid repeated downloads
        global _CHROMEDRIVER_PATH
        if _CHROMEDRIVER_PATH is None:
            _CHROMEDRIVER_PATH = ChromeDriverManager().install()
        
        service = Service(_CHROMEDRIVER_PATH)
        return webdriver.Chrome(service=service, options=chrome_options)


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