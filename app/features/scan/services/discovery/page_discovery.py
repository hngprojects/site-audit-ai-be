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
    def discover_pages(url: str, max_pages: int = 50) -> List[str]:
        # Create temp directory for Chrome user data to avoid DevToolsActivePort issues
        temp_dir = tempfile.mkdtemp()
        
        # chrome_options = Options()
        
        # # Core headless options
        # chrome_options.add_argument("--headless=new")
        # chrome_options.add_argument("--disable-gpu")
        # chrome_options.add_argument("--no-sandbox")
        # chrome_options.add_argument("--disable-dev-shm-usage")

        chrome_options = Options()
        chrome_options.add_argument('--headless')  # Headless mode
        chrome_options.add_argument('--no-sandbox')  

        
        # # Critical: Use temp directory for user data
        # chrome_options.add_argument(f"--user-data-dir={temp_dir}")
        # chrome_options.add_argument("--data-path={}".format(os.path.join(temp_dir, "data")))
        # chrome_options.add_argument("--disk-cache-dir={}".format(os.path.join(temp_dir, "cache")))
        
        # # Disable DevTools completely
        # chrome_options.add_argument("--disable-dev-tools")
        # chrome_options.add_argument("--remote-debugging-port=0")
        
        # # Performance and stability options
        # chrome_options.add_argument("--disable-extensions")
        # chrome_options.add_argument("--disable-software-rasterizer")
        # chrome_options.add_argument("--disable-background-networking")
        # chrome_options.add_argument("--disable-default-apps")
        # chrome_options.add_argument("--disable-sync")
        # chrome_options.add_argument("--disable-translate")
        # chrome_options.add_argument("--mute-audio")
        # chrome_options.add_argument("--hide-scrollbars")
        # chrome_options.add_argument("--metrics-recording-only")
        # chrome_options.add_argument("--no-first-run")
        # chrome_options.add_argument("--safebrowsing-disable-auto-update")
        # chrome_options.add_argument("--ignore-certificate-errors")
        # chrome_options.add_argument("--window-size=1920,1080")
        # chrome_options.add_argument("--start-maximized")
        
        # # Disable automation flags
        # chrome_options.add_experimental_option("excludeSwitches", ["enable-logging", "enable-automation"])
        # chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # # Use webdriver-manager with caching to avoid repeated downloads
        # global _CHROMEDRIVER_PATH
        # if _CHROMEDRIVER_PATH is None:
        #     _CHROMEDRIVER_PATH = ChromeDriverManager().install()
        
        # service = Service(_CHROMEDRIVER_PATH)
        # driver = webdriver.Chrome(service=service, options=chrome_options)
        driver_service = Service(executable_path='/usr/local/bin/chromedriver')  
        driver = webdriver.Chrome(service=driver_service, options=chrome_options)
        # driver.get('https://www.google.com')

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