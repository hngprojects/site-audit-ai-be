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
