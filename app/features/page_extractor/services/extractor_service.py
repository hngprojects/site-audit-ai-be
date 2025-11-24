from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, WebDriverException
from typing import Optional, Dict, List



class ExtractorService:
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
        driver = ExtractorService.build_driver()
        driver.set_page_load_timeout(timeout)
        try:
            driver.get(url)
            return driver  # caller is responsible for driver.quit()
        except (TimeoutException, WebDriverException):
            driver.quit()
            raise


    @staticmethod
    def extract_headings(driver: webdriver.Chrome) -> dict:
        headings = {}
        for tag in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            texts = [el.text.strip() for el in driver.find_elements(By.TAG_NAME, tag)]
            headings[tag] = texts
        return headings
    
    @staticmethod
    def extract_images(driver: webdriver.Chrome) -> list:
        images = []
        for img in driver.find_elements(By.TAG_NAME, "img"):
            src = img.get_attribute("src")
            alt = img.get_attribute("alt") or ""
            if src:
                images.append({"src": src, "alt": alt})
        return images



    @staticmethod
    def extract_accessibility(
        driver: webdriver.Chrome,
        headings: Optional[Dict[str, List[str]]] = None,
        images: Optional[List[dict]] = None,
    ) -> dict:
        """
        Accessibility findings with minimal duplicate DOM queries.
        - Reuses headings/images if provided.
        - Flags missing alt, unlabeled form controls/buttons, icon-only links, empty headings.
        """
        issues = {
            "images_missing_alt": [],
            "inputs_missing_label": [],
            "buttons_missing_label": [],
            "links_missing_label": [],
            "empty_headings": [],
        }

        # Images without alt
        if images is None:
            for img in driver.find_elements(By.TAG_NAME, "img"):
                alt = (img.get_attribute("alt") or "").strip()
                if not alt:
                    issues["images_missing_alt"].append(img.get_attribute("src") or "")
        else:
            for img in images:
                if not (img.get("alt") or "").strip():
                    issues["images_missing_alt"].append(img.get("src", ""))

        # Inputs/select/textarea without a label/aria-label/title or wrapped label
        for inp in driver.find_elements(By.CSS_SELECTOR, "input, textarea, select"):
            itype = (inp.get_attribute("type") or "").lower()
            if itype in {"hidden"}:
                continue
            has_label = False
            # aria/title
            if (inp.get_attribute("aria-label") or "").strip() or (inp.get_attribute("title") or "").strip():
                has_label = True
            # label[for]
            input_id = inp.get_attribute("id")
            if not has_label and input_id:
                label = driver.find_elements(By.CSS_SELECTOR, f"label[for='{input_id}']")
                has_label = any(label)
            # wrapped label
            if not has_label:
                parent = inp.find_element(By.XPATH, "ancestor::label[1]") if inp else None
                has_label = bool(parent)
            if not has_label:
                issues["inputs_missing_label"].append(inp.get_attribute("name") or input_id or itype or "")

        # Buttons and input[type=button|submit|reset] without visible/aria/title text
        for btn in driver.find_elements(By.CSS_SELECTOR, "button, input[type='button'], input[type='submit'], input[type='reset']"):
            label = (
                (btn.text or "").strip()
                or (btn.get_attribute("value") or "").strip()
                or (btn.get_attribute("aria-label") or "").strip()
                or (btn.get_attribute("title") or "").strip()
            )
            if not label:
                issues["buttons_missing_label"].append(btn.get_attribute("id") or btn.get_attribute("name") or "")

        # Links that are icon-only (no text and no aria-label/title)
        for link in driver.find_elements(By.TAG_NAME, "a"):
            label = (
                (link.text or "").strip()
                or (link.get_attribute("aria-label") or "").strip()
                or (link.get_attribute("title") or "").strip()
            )
            if not label:
                issues["links_missing_label"].append(link.get_attribute("href") or "")

        # Headings that exist but are empty
        if headings is None:
            for tag in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                for el in driver.find_elements(By.TAG_NAME, tag):
                    if not (el.text or "").strip():
                        issues["empty_headings"].append(tag)
        else:
            for tag, texts in headings.items():
                issues["empty_headings"].extend([tag] * sum(1 for t in texts if not (t or "").strip()))

        return issues
