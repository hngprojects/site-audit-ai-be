import os
import tempfile
import time
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from typing import Dict, Any
from app.platform.config import settings

_CHROMEDRIVER_PATH = None


class ScrapingService:
    @staticmethod
    def build_driver() -> webdriver.Chrome:
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        if settings.CHROMEDRIVER_PATH:
            driver_service = Service(executable_path=settings.CHROMEDRIVER_PATH)
            driver = webdriver.Chrome(service=driver_service, options=chrome_options)
        else:
            driver = webdriver.Chrome(options=chrome_options)
        
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
            start_time = time.time()
            driver.get(url)
            end_time = time.time()
            
            # Attach performance metrics to driver
            driver.performance_metrics = {
                "load_time": end_time - start_time
            }
            
            return driver  # caller is responsible for driver.quit()
        except (TimeoutException, WebDriverException):
            driver.quit()
            raise
    
    
    @staticmethod
    def calculate_performance_score(load_time: float) -> int:
        """
        Calculate performance score (0-100) based on load time.
        < 0.5s = 100
        > 10s = 0
        Linear interpolation in between.
        """
        if load_time <= 0.5:
            return 100
        if load_time >= 10.0:
            return 0
            
        # Linear interpolation between 0.5s (100) and 10s (0)
        # Slope = (0 - 100) / (10 - 0.5) = -100 / 9.5
        slope = -100 / 9.5
        score = 100 + slope * (load_time - 0.5)
        return int(max(0, min(100, score)))


    @staticmethod
    def get_performance_comment(score: int) -> str:
        """Return a text comment based on the performance score."""
        if score >= 90:
            return "Excellent! The page loads very quickly."
        elif score >= 75:
            return "Good. The page load time is acceptable."
        elif score >= 50:
            return "Fair. The page could load faster."
        elif score >= 25:
            return "Poor. The page is slow to load."
        else:
            return "Critical. The page takes too long to load."


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
            
            # Get performance metrics
            load_time = getattr(driver, "performance_metrics", {}).get("load_time", 0.0)
            performance_score = ScrapingService.calculate_performance_score(load_time)
            performance_comment = ScrapingService.get_performance_comment(performance_score)
            
            return {
                "url": url,
                "current_url": current_url,  # Final URL after redirects
                "html": html_content,
                "page_title": page_title,
                "content_length": len(html_content),
                "load_time": load_time,
                "performance_score": performance_score,
                "performance_comment": performance_comment,
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