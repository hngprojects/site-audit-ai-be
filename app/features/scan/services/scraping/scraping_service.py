from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium import webdriver


class ScrapingService:
    @staticmethod
    def build_driver() -> webdriver.Chrome:
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.set_capability("pageLoadStrategy", "eager")  # stop waiting for subresources
        return webdriver.Chrome(options=chrome_options)


    @staticmethod
    def load_page(url: str, timeout: int = 10) -> webdriver.Chrome:
        driver = ScrapingService.build_driver()
        driver.set_page_load_timeout(timeout)
        try:
            driver.get(url)
            return driver  # caller is responsible for driver.quit()
        except (TimeoutException, WebDriverException):
            driver.quit()
            raise