from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

class SeleniumService:
    def scrape_url(self, url: str):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        driver = None
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.get(url)
            
            title = driver.title
            content = driver.find_element("tag name", "body").text
            
            return {
                "url": url,
                "title": title,
                "content_preview": content[:500] + "..." if len(content) > 500 else content
            }
        finally:
            if driver:
                driver.quit()
