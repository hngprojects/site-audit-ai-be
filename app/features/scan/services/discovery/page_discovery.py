import logging
from typing import List
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
import tempfile
import os

# Cache ChromeDriver path to avoid repeated downloads
_CHROMEDRIVER_PATH = None

logger = logging.getLogger(__name__)


class PageDiscoveryService:
    
    @staticmethod
    def discover_pages(url: str, max_pages: int = 100) -> List[str]:
        # Create temp directory for Chrome user data to avoid DevToolsActivePort issues
        temp_dir = tempfile.mkdtemp()
        
        chrome_options = Options()
        
        # Essential flags for headless Chrome on Linux VPS
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        
        # Use temp directory to avoid profile conflicts
        chrome_options.add_argument(f"--user-data-dir={temp_dir}")
        
        # Additional stability flags
        chrome_options.add_argument("--disable-setuid-sandbox")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-software-rasterizer")
        chrome_options.add_argument("--no-first-run")
        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # Suppress unnecessary output
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
        
        # Use webdriver-manager with caching to avoid repeated downloads
        global _CHROMEDRIVER_PATH
        if _CHROMEDRIVER_PATH is None:
            _CHROMEDRIVER_PATH = ChromeDriverManager().install()
        
        service = Service(_CHROMEDRIVER_PATH)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.get(url)
        visited = set()
        to_visit = [url]
        pages = []

        while to_visit and len(visited) < max_pages:
            current = to_visit.pop()
            if current in visited:
                continue
            visited.add(current)
            driver.get(current)
            pages.append(current)
            links = driver.find_elements(By.TAG_NAME, "a")
            for link in links:
                href = link.get_attribute("href")
                if href and href.startswith(url) and href not in visited:
                    to_visit.append(href)
        driver.quit()
        return pages
