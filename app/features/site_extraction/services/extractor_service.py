from typing import Optional, List
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

from app.features.site_extraction.schemas.metadata import (
    MetadataExtractionResult,
    TitleMetadata,
    DescriptionMetadata,
    OpenGraphMetadata,
    MetadataIssue,
)


class ExtractorService:
    """Service for extracting metadata from web pages"""
    
    # SEO Best Practice Constants
    TITLE_MIN_LENGTH = 30
    TITLE_MAX_LENGTH = 70
    DESCRIPTION_MIN_LENGTH = 120
    DESCRIPTION_MAX_LENGTH = 160
    
    @staticmethod
    def extract_metadata(driver: WebDriver) -> MetadataExtractionResult:
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
    def _extract_title(driver: WebDriver) -> TitleMetadata:
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
    def _extract_description(driver: WebDriver) -> DescriptionMetadata:
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
    def _extract_keywords(driver: WebDriver) -> Optional[str]:
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
    def _extract_open_graph(driver: WebDriver) -> Optional[OpenGraphMetadata]:
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
    def _extract_canonical_url(driver: WebDriver) -> Optional[str]:
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
    def _extract_viewport(driver: WebDriver) -> Optional[str]:
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