import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, WebDriverException

class SiteScraperService:
    def __init__(self):
        self.chrome_options = Options()
        self.chrome_options.add_argument("--headless") 
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")
        self.chrome_options.add_argument("--log-level=3")

    def load_page(self, driver, url):
        """Safely loads the URL with a timeout."""
        try:
            driver.set_page_load_timeout(30) 
            driver.get(url)
            return True
        except TimeoutException:
            print(f"Timeout loading {url}")
            return False
        except WebDriverException as e:
            print(f"Error loading {url}: {e}")
            return False

    def extract_text_content(self, driver, target_keywords=None):
        """Analyzes word count, ratios, readability, and keywords."""
        if target_keywords is None:
            target_keywords = []

        try:
            body_element = driver.find_element(By.TAG_NAME, "body")
            raw_text = body_element.text
        except:
            return {"error": "Could not find body tag"}
        
        clean_text = " ".join(raw_text.split())
        
        # --- CALCULATIONS ---
        words = clean_text.split()
        word_count = len(words)

        # Keyword Density
        keyword_data = {}
        if target_keywords:
            lower_text = clean_text.lower()
            for keyword in target_keywords:
                count = lower_text.count(keyword.lower())
                density = (count / word_count * 100) if word_count > 0 else 0
                keyword_data[keyword] = {"count": count, "density": round(density, 2)}

        # Header Ratio
        headers = driver.find_elements(By.CSS_SELECTOR, "h1, h2, h3, h4, h5, h6")
        header_text = " ".join([h.text for h in headers])
        header_word_count = len(header_text.split())
        hb_ratio = (header_word_count / word_count) if word_count > 0 else 0

        # Readability
        sentence_count = len(re.split(r'[.!?]+', clean_text)) or 1
        syllable_count = sum(1 for char in clean_text.lower() if char in "aeiouy")
        
        avg_sentence_len = word_count / sentence_count
        avg_syllables_per_word = syllable_count / word_count if word_count > 0 else 0
        
        readability_score = 206.835 - (1.015 * avg_sentence_len) - (84.6 * avg_syllables_per_word)

        return {
            "word_count": word_count,
            "header_body_ratio": round(hb_ratio, 2),
            "readability_score": round(readability_score, 2),
            "keyword_analysis": keyword_data
        }

    def perform_text_scraping(self, url: str, keywords: list = None):
        """Orchestrator: Opens driver -> Runs Check -> Returns Raw Data"""
        driver = webdriver.Chrome(options=self.chrome_options)
        try:
            loaded = self.load_page(driver, url)
            
            if not loaded:
                return {"error": "Page failed to load"}

            # Return the result
            return self.extract_text_content(driver, keywords)
            
        except Exception as e:
            return {"error": str(e)}
        finally:
            driver.quit()
            

