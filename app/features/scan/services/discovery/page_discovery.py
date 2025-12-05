import os
import logging
import tempfile
from typing import List
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from app.platform.config import settings

_CHROMEDRIVER_PATH = None

logger = logging.getLogger(__name__)

class PageDiscoveryService:
    
    @staticmethod
    def discover_pages(url: str, max_pages: int = 15) -> List[str]:
        """
        Discover pages from a website using Selenium.
        
        Args:
            url: Base URL to start discovery from
            max_pages: Maximum number of pages to discover (default: 15)
            
        Returns:
            List of discovered URLs (all from same base domain)
        """
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        if settings.CHROMEDRIVER_PATH:
            driver_service = Service(executable_path=settings.CHROMEDRIVER_PATH)
            driver = webdriver.Chrome(service=driver_service, options=chrome_options)
        else:
            driver = webdriver.Chrome(options=chrome_options)

        try:
            # Parse base URL for domain validation
            base_parsed = urlparse(url)
            base_domain = f"{base_parsed.scheme}://{base_parsed.netloc}"
            
            driver.get(url)
            visited = set()
            to_visit = [url]
            pages = []

            while to_visit and len(visited) < max_pages:
                current = to_visit.pop(0)  # Use BFS (pop from front)
                if current in visited:
                    continue
                visited.add(current)
                
                try:
                    driver.get(current)
                    pages.append(current)
                    
                    links = driver.find_elements(By.TAG_NAME, "a")
                    for link in links:
                        href = link.get_attribute("href")
                        if href and PageDiscoveryService._is_same_domain(href, base_domain):
                            if href not in visited and href not in to_visit:
                                to_visit.append(href)
                except Exception as e:
                    logger.warning(f"Failed to load page {current}: {e}")
                    continue
                    
            logger.info(f"Discovered {len(pages)} pages from {url}")
            return pages
        finally:
            driver.quit()
    
    @staticmethod
    def _is_same_domain(url: str, base_domain: str) -> bool:
        """
        Check if URL belongs to the same domain as base.
        
        Args:
            url: URL to check
            base_domain: Base domain (e.g., "https://example.com")
            
        Returns:
            True if URL is from same domain, False otherwise
        """
        try:
            parsed = urlparse(url)
            # Ensure URL has a valid scheme and netloc
            if not parsed.scheme or not parsed.netloc:
                return False
            url_domain = f"{parsed.scheme}://{parsed.netloc}"
            return url_domain == base_domain
        except Exception:
            return False