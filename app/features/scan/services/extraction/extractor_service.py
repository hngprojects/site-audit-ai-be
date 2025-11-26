from selenium import webdriver
from selenium.webdriver.common.by import By
from typing import Optional, Dict, List
from app.features.scan.schemas.metadata import (
    MetadataExtractionResult,
    TitleMetadata,
    DescriptionMetadata,
    OpenGraphMetadata,
    MetadataIssue,
)
from selenium.common.exceptions import NoSuchElementException
import re


class ExtractorService:
    # SEO Best Practice Constants
    TITLE_MIN_LENGTH = 30
    TITLE_MAX_LENGTH = 70
    DESCRIPTION_MIN_LENGTH = 120
    DESCRIPTION_MAX_LENGTH = 160    


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


    @staticmethod
    def _extract_title(driver: webdriver.Chrome) -> TitleMetadata:
        """Extract and validate page title"""
        issues: List[MetadataIssue] = []
        
        try:
            title_element = driver.find_element(By.TAG_NAME, "title")
            title_value = title_element.text.strip() if title_element else None
        except NoSuchElementException:
            title_value = None
        
        # Handle missing title
        if not title_value:
            issues.append(MetadataIssue(
                field="title",
                severity="error",
                message="Page title is missing. Every page should have a <title> tag."
            ))
            return TitleMetadata(
                value=None,
                length=0,
                is_valid=False,
                issues=issues
            )
        
        title_length = len(title_value)
        
        # Validate title length
        if title_length < ExtractorService.TITLE_MIN_LENGTH:
            issues.append(MetadataIssue(
                field="title",
                severity="warning",
                message=f"Title is too short ({title_length} chars). Recommended: {ExtractorService.TITLE_MIN_LENGTH}-{ExtractorService.TITLE_MAX_LENGTH} characters for optimal SEO."
            ))
        elif title_length > ExtractorService.TITLE_MAX_LENGTH:
            issues.append(MetadataIssue(
                field="title",
                severity="warning",
                message=f"Title is too long ({title_length} chars). Recommended: {ExtractorService.TITLE_MIN_LENGTH}-{ExtractorService.TITLE_MAX_LENGTH} characters. Long titles may be truncated in search results."
            ))
        
        is_valid = len(issues) == 0
        
        return TitleMetadata(
            value=title_value,
            length=title_length,
            is_valid=is_valid,
            issues=issues
        )
    

    @staticmethod
    def _extract_description(driver: webdriver.Chrome) -> DescriptionMetadata:
        """Extract and validate meta description"""
        issues: List[MetadataIssue] = []
        
        try:
            description_element = driver.find_element(
                By.CSS_SELECTOR, 
                'meta[name="description"]'
            )
            description_value = description_element.get_attribute("content")
            description_value = description_value.strip() if description_value else None
        except NoSuchElementException:
            description_value = None
        
        # Handle missing description
        if not description_value:
            issues.append(MetadataIssue(
                field="description",
                severity="error",
                message='Meta description is missing. Add a <meta name="description" content="..."> tag for better SEO.'
            ))
            return DescriptionMetadata(
                value=None,
                length=0,
                is_valid=False,
                issues=issues
            )
        
        description_length = len(description_value)
        
        # Validate description length
        if description_length < ExtractorService.DESCRIPTION_MIN_LENGTH:
            issues.append(MetadataIssue(
                field="description",
                severity="warning",
                message=f"Description is too short ({description_length} chars). Recommended: {ExtractorService.DESCRIPTION_MIN_LENGTH}-{ExtractorService.DESCRIPTION_MAX_LENGTH} characters for optimal display in search results."
            ))
        elif description_length > ExtractorService.DESCRIPTION_MAX_LENGTH:
            issues.append(MetadataIssue(
                field="description",
                severity="warning",
                message=f"Description is too long ({description_length} chars). Recommended: {ExtractorService.DESCRIPTION_MIN_LENGTH}-{ExtractorService.DESCRIPTION_MAX_LENGTH} characters. Long descriptions may be truncated in search results."
            ))
        
        is_valid = len(issues) == 0
        
        return DescriptionMetadata(
            value=description_value,
            length=description_length,
            is_valid=is_valid,
            issues=issues
        )
    

    @staticmethod
    def _extract_keywords(driver: webdriver.Chrome) -> Optional[str]:
        """Extract meta keywords (optional, less important in modern SEO)"""
        try:
            keywords_element = driver.find_element(
                By.CSS_SELECTOR, 
                'meta[name="keywords"]'
            )
            keywords_value = keywords_element.get_attribute("content")
            return keywords_value.strip() if keywords_value else None
        except NoSuchElementException:
            return None
    

    @staticmethod
    def _extract_open_graph(driver: webdriver.Chrome) -> Optional[OpenGraphMetadata]:
        """Extract Open Graph tags for social media"""
        og_data = {}
        
        og_tags = {
            "title": 'meta[property="og:title"]',
            "description": 'meta[property="og:description"]',
            "image": 'meta[property="og:image"]',
            "url": 'meta[property="og:url"]',
            "type": 'meta[property="og:type"]',
        }
        
        for key, selector in og_tags.items():
            try:
                element = driver.find_element(By.CSS_SELECTOR, selector)
                content = element.get_attribute("content")
                og_data[key] = content.strip() if content else None
            except NoSuchElementException:
                og_data[key] = None
        
        # Only return OpenGraphMetadata if at least one OG tag exists
        if any(og_data.values()):
            return OpenGraphMetadata(**og_data)
        
        return None
    

    @staticmethod
    def _extract_canonical_url(driver: webdriver.Chrome) -> Optional[str]:
        """Extract canonical URL"""
        try:
            canonical_element = driver.find_element(
                By.CSS_SELECTOR, 
                'link[rel="canonical"]'
            )
            canonical_url = canonical_element.get_attribute("href")
            return canonical_url.strip() if canonical_url else None
        except NoSuchElementException:
            return None
    

    @staticmethod
    def _extract_viewport(driver: webdriver.Chrome) -> Optional[str]:
        """Extract viewport meta tag"""
        try:
            viewport_element = driver.find_element(
                By.CSS_SELECTOR, 
                'meta[name="viewport"]'
            )
            viewport_content = viewport_element.get_attribute("content")
            return viewport_content.strip() if viewport_content else None
        except NoSuchElementException:
            return None
        

    @staticmethod
    def extract_metadata(driver: webdriver.Chrome) -> MetadataExtractionResult:
        """
        Extract and validate metadata from a loaded web page.
        
        Args:
            driver: Selenium WebDriver with a loaded page
            
        Returns:
            MetadataExtractionResult: Structured metadata with validation
            
        Example:
            driver = PageLoaderService.load_page("https://example.com")
            try:
                metadata = ExtractorService.extract_metadata(driver)
                print(f"Title: {metadata.title.value}")
                print(f"Valid: {metadata.overall_valid}")
            finally:
                driver.quit()
        """
        current_url = driver.current_url
        
        # Extract each component
        title = ExtractorService._extract_title(driver)
        description = ExtractorService._extract_description(driver)
        keywords = ExtractorService._extract_keywords(driver)
        open_graph = ExtractorService._extract_open_graph(driver)
        canonical_url = ExtractorService._extract_canonical_url(driver)
        viewport = ExtractorService._extract_viewport(driver)
        
        # Calculate overall metrics
        has_title = title.value is not None and title.value != ""
        has_description = description.value is not None and description.value != ""
        
        total_issues = len(title.issues) + len(description.issues)
        overall_valid = title.is_valid and description.is_valid
        
        return MetadataExtractionResult(
            url=current_url,
            title=title,
            description=description,
            keywords=keywords,
            open_graph=open_graph,
            canonical_url=canonical_url,
            viewport=viewport,
            has_title=has_title,
            has_description=has_description,
            overall_valid=overall_valid,
            total_issues=total_issues,
        )
    

    @staticmethod
    def extract_text_content(driver: webdriver.Chrome, target_keywords=None):
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

