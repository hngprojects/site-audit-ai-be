import os
import logging
import tempfile
import re
from typing import List
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from app.platform.config import settings
from openai import OpenAI

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

    @staticmethod
    def suggest_pages(url: str, max_pages: int = 10) -> List[str]:
        """Suggest likely internal pages using LLM based on the URL."""
        try:
            client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=settings.OPENROUTER_API_KEY
            )
            
            prompt = f"""
            Given the website URL {url}, suggest up to {max_pages} likely internal page URLs that would be important for a website audit.
            Common examples include /about, /contact, /pricing, /services, /blog, /terms, /privacy.
            Infer the likely structure based on the domain name if possible.
            Return ONLY the full URLs, one per line.
            """

            completion = client.chat.completions.create(
                model="z-ai/glm-4.5-air:free",
                messages=[{"role": "user", "content": prompt}],
                extra_headers={
                    "HTTP-Referer": url,
                    "X-Title": "Site Audit Discovery",
                },
            )
            
            text = completion.choices[0].message.content or ""
            
            # Extract URLs
            urls = re.findall(r'https?://[^\s<>"\']+', text)
            
            # Handle relative paths or plain text paths if full URLs aren't returned
            if not urls:
                lines = text.splitlines()
                base_url = url.rstrip('/')
                for line in lines:
                    line = line.strip()
                    # Remove common list markers
                    line = re.sub(r'^[\d]+[.\)]\s*', '', line)
                    line = re.sub(r'^[-*•]\s*', '', line)
                    
                    if not line:
                        continue
                        
                    if line.startswith('/'):
                        urls.append(base_url + line)
                    elif re.match(r'^[a-zA-Z0-9\-_/]+$', line):
                        urls.append(base_url + '/' + line.lstrip('/'))
            
            # Filter to ensure they belong to the domain (basic check)
            domain_match = re.search(r'https?://([^/]+)', url)
            if domain_match:
                domain = domain_match.group(1)
                urls = [u for u in urls if domain in u]

            return list(set(urls))[:max_pages]
        except Exception as e:
            logger.error(f"LLM page suggestion failed: {e}")
            return []