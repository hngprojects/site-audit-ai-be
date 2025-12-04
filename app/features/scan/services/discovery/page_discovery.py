import os
import logging
import tempfile
from typing import List
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
    def discover_pages(url: str, max_pages: int = 1) -> List[str]:
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
            return pages
        finally:
            driver.quit()