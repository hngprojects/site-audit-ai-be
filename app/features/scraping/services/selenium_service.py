from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import logging

logger = logging.getLogger(__name__)

class SeleniumService:
    def scrape_url(self, url: str) -> dict:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        driver = None
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            logger.info(f"Navigating to {url}")
            driver.get(url)
            
            title = driver.title
            body_text = driver.find_element("tag name", "body").text
            content_preview = body_text[:500] + "..." if len(body_text) > 500 else body_text
            
            return {
                "url": url,
                "title": title,
                "content_preview": content_preview
            }
        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")
            raise e
        finally:
            if driver:
                driver.quit()
