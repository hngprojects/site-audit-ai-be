"""
Comprehensive Selenium-based Web Scraping Service

This service handles complete page scraping and data extraction using Selenium WebDriver.
It extracts metadata, content, performance metrics, accessibility data, and design signals.
"""

import logging
import time
import re
from typing import Dict, List, Any, Optional, Tuple
from urllib.parse import urlparse, urljoin
from collections import Counter

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

logger = logging.getLogger(__name__)


class ScrapingService:
    """
    Comprehensive web scraping service using Selenium.
    
    Extracts:
    - Metadata (title, description, meta tags)
    - Headings hierarchy (h1-h6)
    - Images (src, alt, dimensions)
    - Links (internal, external, broken)
    - Performance metrics (TTFB, load time)
    - Accessibility features (ARIA, semantic HTML)
    - Design signals (colors, fonts, spacing)
    - Text content (word count, readability)
    """
    
    def __init__(self, headless: bool = True, timeout: int = 30):
        """
        Initialize the scraping service.
        
        Args:
            headless: Run browser in headless mode
            timeout: Default timeout for page loads (seconds)
        """
        self.headless = headless
        self.timeout = timeout
        self.driver = None
    
    def load_page(self, url: str) -> webdriver.Chrome:
        """
        Initialize Selenium WebDriver and load the page.
        
        Args:
            url: URL to load
            
        Returns:
            Selenium WebDriver instance
            
        Raises:
            WebDriverException: If page fails to load
        """
        try:
            # Configure Chrome options
            chrome_options = Options()
            if self.headless:
                chrome_options.add_argument("--headless")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            
            # Initialize driver
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(self.timeout)
            
            # Record start time for performance metrics
            start_time = time.time()
            
            # Load the page
            logger.info(f"Loading page: {url}")
            self.driver.get(url)
            
            # Wait for page to be ready
            WebDriverWait(self.driver, self.timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            
            load_time = (time.time() - start_time) * 1000  # Convert to ms
            logger.info(f"Page loaded in {load_time:.2f}ms")
            
            return self.driver
            
        except TimeoutException:
            logger.error(f"Timeout loading page: {url}")
            raise
        except WebDriverException as e:
            logger.error(f"WebDriver error loading page {url}: {str(e)}")
            raise
    
    def extract_metadata(self, driver: webdriver.Chrome) -> Dict[str, Any]:
        """
        Extract page metadata including title, description, and meta tags.
        
        Args:
            driver: Selenium WebDriver instance
            
        Returns:
            Dictionary containing metadata
        """
        metadata = {
            "title": "",
            "description": "",
            "keywords": "",
            "author": "",
            "canonical_url": "",
            "og_tags": {},
            "twitter_tags": {},
            "meta_tags": []
        }
        
        try:
            # Extract title
            metadata["title"] = driver.title or ""
            
            # Extract meta tags
            meta_elements = driver.find_elements(By.TAG_NAME, "meta")
            
            for meta in meta_elements:
                name = meta.get_attribute("name") or ""
                property_attr = meta.get_attribute("property") or ""
                content = meta.get_attribute("content") or ""
                
                # Standard meta tags
                if name.lower() == "description":
                    metadata["description"] = content
                elif name.lower() == "keywords":
                    metadata["keywords"] = content
                elif name.lower() == "author":
                    metadata["author"] = content
                
                # Open Graph tags
                elif property_attr.startswith("og:"):
                    metadata["og_tags"][property_attr] = content
                
                # Twitter Card tags
                elif name.startswith("twitter:"):
                    metadata["twitter_tags"][name] = content
                
                # Store all meta tags
                if name or property_attr:
                    metadata["meta_tags"].append({
                        "name": name,
                        "property": property_attr,
                        "content": content
                    })
            
            # Extract canonical URL
            try:
                canonical = driver.find_element(By.CSS_SELECTOR, "link[rel='canonical']")
                metadata["canonical_url"] = canonical.get_attribute("href") or ""
            except NoSuchElementException:
                pass
            
            logger.info(f"Extracted metadata: title='{metadata['title'][:50]}...'")
            
        except Exception as e:
            logger.error(f"Error extracting metadata: {str(e)}")
        
        return metadata
    
    def extract_headings(self, driver: webdriver.Chrome) -> Dict[str, Any]:
        """
        Extract heading hierarchy (h1-h6).
        
        Args:
            driver: Selenium WebDriver instance
            
        Returns:
            Dictionary containing heading data and hierarchy analysis
        """
        headings_data = {
            "h1": [],
            "h2": [],
            "h3": [],
            "h4": [],
            "h5": [],
            "h6": [],
            "hierarchy": [],
            "issues": []
        }
        
        try:
            # Extract all headings
            for level in range(1, 7):
                tag = f"h{level}"
                elements = driver.find_elements(By.TAG_NAME, tag)
                
                for elem in elements:
                    text = elem.text.strip()
                    if text:
                        headings_data[tag].append(text)
                        headings_data["hierarchy"].append({
                            "level": level,
                            "text": text
                        })
            
            # Analyze heading structure
            h1_count = len(headings_data["h1"])
            
            if h1_count == 0:
                headings_data["issues"].append("Missing H1 heading")
            elif h1_count > 1:
                headings_data["issues"].append(f"Multiple H1 headings found ({h1_count})")
            
            logger.info(f"Extracted {len(headings_data['hierarchy'])} headings")
            
        except Exception as e:
            logger.error(f"Error extracting headings: {str(e)}")
        
        return headings_data
    
    def extract_images(self, driver: webdriver.Chrome) -> Dict[str, Any]:
        """
        Extract image data including src, alt text, and dimensions.
        
        Args:
            driver: Selenium WebDriver instance
            
        Returns:
            Dictionary containing image data and accessibility issues
        """
        images_data = {
            "images": [],
            "total_count": 0,
            "missing_alt_count": 0,
            "issues": []
        }
        
        try:
            img_elements = driver.find_elements(By.TAG_NAME, "img")
            images_data["total_count"] = len(img_elements)
            
            for img in img_elements:
                src = img.get_attribute("src") or ""
                alt = img.get_attribute("alt")
                width = img.get_attribute("width") or img.get_attribute("naturalWidth")
                height = img.get_attribute("height") or img.get_attribute("naturalHeight")
                
                image_info = {
                    "src": src,
                    "alt": alt if alt is not None else "",
                    "has_alt": alt is not None and alt.strip() != "",
                    "width": width,
                    "height": height
                }
                
                images_data["images"].append(image_info)
                
                # Check for missing alt text
                if not image_info["has_alt"]:
                    images_data["missing_alt_count"] += 1
            
            if images_data["missing_alt_count"] > 0:
                images_data["issues"].append(
                    f"{images_data['missing_alt_count']} images missing alt text"
                )
            
            logger.info(f"Extracted {images_data['total_count']} images")
            
        except Exception as e:
            logger.error(f"Error extracting images: {str(e)}")
        
        return images_data
    
    def extract_links(self, driver: webdriver.Chrome, base_url: str) -> Dict[str, Any]:
        """
        Extract and categorize links (internal, external, broken).
        
        Args:
            driver: Selenium WebDriver instance
            base_url: Base URL of the site for determining internal vs external
            
        Returns:
            Dictionary containing link data and categorization
        """
        links_data = {
            "internal_links": [],
            "external_links": [],
            "broken_links": [],
            "total_count": 0,
            "internal_count": 0,
            "external_count": 0,
            "issues": []
        }
        
        try:
            base_domain = urlparse(base_url).netloc
            anchor_elements = driver.find_elements(By.TAG_NAME, "a")
            links_data["total_count"] = len(anchor_elements)
            
            for anchor in anchor_elements:
                href = anchor.get_attribute("href")
                text = anchor.text.strip()
                
                if not href:
                    continue
                
                # Resolve relative URLs
                absolute_url = urljoin(base_url, href)
                parsed_url = urlparse(absolute_url)
                
                link_info = {
                    "url": absolute_url,
                    "text": text,
                    "has_text": bool(text)
                }
                
                # Categorize as internal or external
                if parsed_url.netloc == base_domain or parsed_url.netloc == "":
                    links_data["internal_links"].append(link_info)
                    links_data["internal_count"] += 1
                else:
                    links_data["external_links"].append(link_info)
                    links_data["external_count"] += 1
                
                # Check for empty link text (accessibility issue)
                if not text and not anchor.find_elements(By.TAG_NAME, "img"):
                    links_data["issues"].append(f"Link with no text: {absolute_url}")
            
            logger.info(
                f"Extracted {links_data['total_count']} links "
                f"({links_data['internal_count']} internal, {links_data['external_count']} external)"
            )
            
        except Exception as e:
            logger.error(f"Error extracting links: {str(e)}")
        
        return links_data
    
    def extract_performance_metrics(self, driver: webdriver.Chrome) -> Dict[str, Any]:
        """
        Extract performance metrics using Navigation Timing API.
        
        Args:
            driver: Selenium WebDriver instance
            
        Returns:
            Dictionary containing performance metrics
        """
        metrics = {
            "ttfb_ms": None,
            "dom_load_ms": None,
            "page_load_ms": None,
            "dom_interactive_ms": None,
            "resource_count": 0,
            "total_size_kb": 0
        }
        
        try:
            # Get Navigation Timing API data
            timing = driver.execute_script("""
                var timing = window.performance.timing;
                var navigation = window.performance.navigation;
                return {
                    navigationStart: timing.navigationStart,
                    responseStart: timing.responseStart,
                    domInteractive: timing.domInteractive,
                    domContentLoadedEventEnd: timing.domContentLoadedEventEnd,
                    loadEventEnd: timing.loadEventEnd
                };
            """)
            
            if timing:
                nav_start = timing.get("navigationStart", 0)
                
                # Calculate TTFB (Time to First Byte)
                if timing.get("responseStart"):
                    metrics["ttfb_ms"] = timing["responseStart"] - nav_start
                
                # Calculate DOM Interactive time
                if timing.get("domInteractive"):
                    metrics["dom_interactive_ms"] = timing["domInteractive"] - nav_start
                
                # Calculate DOM Load time
                if timing.get("domContentLoadedEventEnd"):
                    metrics["dom_load_ms"] = timing["domContentLoadedEventEnd"] - nav_start
                
                # Calculate full page load time
                if timing.get("loadEventEnd"):
                    metrics["page_load_ms"] = timing["loadEventEnd"] - nav_start
            
            # Get resource timing data
            resources = driver.execute_script("""
                var resources = window.performance.getEntriesByType('resource');
                return resources.map(function(r) {
                    return {
                        name: r.name,
                        duration: r.duration,
                        size: r.transferSize || 0
                    };
                });
            """)
            
            if resources:
                metrics["resource_count"] = len(resources)
                total_size = sum(r.get("size", 0) for r in resources)
                metrics["total_size_kb"] = round(total_size / 1024, 2)
            
            logger.info(f"Performance metrics: TTFB={metrics['ttfb_ms']}ms, Load={metrics['page_load_ms']}ms")
            
        except Exception as e:
            logger.error(f"Error extracting performance metrics: {str(e)}")
        
        return metrics
    
    def extract_accessibility(self, driver: webdriver.Chrome) -> Dict[str, Any]:
        """
        Extract accessibility features and issues.
        
        Args:
            driver: Selenium WebDriver instance
            
        Returns:
            Dictionary containing accessibility data
        """
        accessibility_data = {
            "has_lang_attribute": False,
            "lang_value": "",
            "aria_labels_count": 0,
            "aria_roles_count": 0,
            "form_labels_count": 0,
            "form_inputs_count": 0,
            "unlabeled_inputs": 0,
            "semantic_elements": {},
            "issues": []
        }
        
        try:
            # Check for lang attribute
            html_element = driver.find_element(By.TAG_NAME, "html")
            lang = html_element.get_attribute("lang")
            accessibility_data["has_lang_attribute"] = bool(lang)
            accessibility_data["lang_value"] = lang or ""
            
            if not lang:
                accessibility_data["issues"].append("Missing lang attribute on <html>")
            
            # Count ARIA labels and roles
            aria_label_elements = driver.find_elements(By.CSS_SELECTOR, "[aria-label]")
            accessibility_data["aria_labels_count"] = len(aria_label_elements)
            
            aria_role_elements = driver.find_elements(By.CSS_SELECTOR, "[role]")
            accessibility_data["aria_roles_count"] = len(aria_role_elements)
            
            # Check form accessibility
            form_inputs = driver.find_elements(By.CSS_SELECTOR, "input, textarea, select")
            accessibility_data["form_inputs_count"] = len(form_inputs)
            
            labels = driver.find_elements(By.TAG_NAME, "label")
            accessibility_data["form_labels_count"] = len(labels)
            
            # Count unlabeled inputs
            for input_elem in form_inputs:
                input_id = input_elem.get_attribute("id")
                aria_label = input_elem.get_attribute("aria-label")
                aria_labelledby = input_elem.get_attribute("aria-labelledby")
                
                # Check if input has associated label
                has_label = False
                if input_id:
                    try:
                        driver.find_element(By.CSS_SELECTOR, f"label[for='{input_id}']")
                        has_label = True
                    except NoSuchElementException:
                        pass
                
                if not (has_label or aria_label or aria_labelledby):
                    accessibility_data["unlabeled_inputs"] += 1
            
            if accessibility_data["unlabeled_inputs"] > 0:
                accessibility_data["issues"].append(
                    f"{accessibility_data['unlabeled_inputs']} form inputs without labels"
                )
            
            # Count semantic HTML5 elements
            semantic_tags = ["header", "nav", "main", "article", "section", "aside", "footer"]
            for tag in semantic_tags:
                elements = driver.find_elements(By.TAG_NAME, tag)
                accessibility_data["semantic_elements"][tag] = len(elements)
            
            logger.info(f"Accessibility check: {len(accessibility_data['issues'])} issues found")
            
        except Exception as e:
            logger.error(f"Error extracting accessibility data: {str(e)}")
        
        return accessibility_data
    
    def extract_design_signals(self, driver: webdriver.Chrome) -> Dict[str, Any]:
        """
        Extract design-related signals: colors, fonts, spacing, viewport.
        
        Args:
            driver: Selenium WebDriver instance
            
        Returns:
            Dictionary containing design data
        """
        design_data = {
            "viewport": {},
            "colors": {
                "background_colors": [],
                "text_colors": [],
                "unique_colors": 0
            },
            "fonts": {
                "font_families": [],
                "unique_fonts": 0
            },
            "spacing": {},
            "contrast_issues": []
        }
        
        try:
            # Get viewport dimensions
            viewport = driver.execute_script("""
                return {
                    width: window.innerWidth,
                    height: window.innerHeight,
                    devicePixelRatio: window.devicePixelRatio
                };
            """)
            design_data["viewport"] = viewport
            
            # Extract colors from body and major elements
            color_script = """
                var colors = {backgrounds: [], texts: []};
                var elements = document.querySelectorAll('body, div, section, header, footer, p, h1, h2, h3, span');
                
                elements.forEach(function(el) {
                    var style = window.getComputedStyle(el);
                    var bgColor = style.backgroundColor;
                    var textColor = style.color;
                    
                    if (bgColor && bgColor !== 'rgba(0, 0, 0, 0)') {
                        colors.backgrounds.push(bgColor);
                    }
                    if (textColor) {
                        colors.texts.push(textColor);
                    }
                });
                
                return colors;
            """
            
            colors = driver.execute_script(color_script)
            if colors:
                # Get unique colors
                bg_colors = list(set(colors.get("backgrounds", [])))
                text_colors = list(set(colors.get("texts", [])))
                
                design_data["colors"]["background_colors"] = bg_colors[:10]  # Limit to top 10
                design_data["colors"]["text_colors"] = text_colors[:10]
                design_data["colors"]["unique_colors"] = len(bg_colors) + len(text_colors)
            
            # Extract font families
            font_script = """
                var fonts = new Set();
                var elements = document.querySelectorAll('body, p, h1, h2, h3, h4, h5, h6, span, a');
                
                elements.forEach(function(el) {
                    var style = window.getComputedStyle(el);
                    var fontFamily = style.fontFamily;
                    if (fontFamily) {
                        fonts.add(fontFamily);
                    }
                });
                
                return Array.from(fonts);
            """
            
            fonts = driver.execute_script(font_script)
            if fonts:
                design_data["fonts"]["font_families"] = fonts[:10]  # Limit to top 10
                design_data["fonts"]["unique_fonts"] = len(fonts)
            
            logger.info(f"Design signals: {design_data['colors']['unique_colors']} colors, {design_data['fonts']['unique_fonts']} fonts")
            
        except Exception as e:
            logger.error(f"Error extracting design signals: {str(e)}")
        
        return design_data
    
    def extract_text_content(self, driver: webdriver.Chrome) -> Dict[str, Any]:
        """
        Extract and analyze text content: word count, readability, keyword density.
        
        Args:
            driver: Selenium WebDriver instance
            
        Returns:
            Dictionary containing text analysis
        """
        text_data = {
            "word_count": 0,
            "character_count": 0,
            "paragraph_count": 0,
            "sentence_count": 0,
            "avg_words_per_sentence": 0,
            "top_keywords": [],
            "readability_score": None
        }
        
        try:
            # Extract main text content (excluding scripts, styles)
            text_script = """
                var clone = document.body.cloneNode(true);
                var scripts = clone.querySelectorAll('script, style, noscript');
                scripts.forEach(function(el) { el.remove(); });
                return clone.innerText || clone.textContent;
            """
            
            text_content = driver.execute_script(text_script)
            
            if text_content:
                # Clean and analyze text
                text_content = text_content.strip()
                text_data["character_count"] = len(text_content)
                
                # Word count
                words = re.findall(r'\b\w+\b', text_content.lower())
                text_data["word_count"] = len(words)
                
                # Sentence count (approximate)
                sentences = re.split(r'[.!?]+', text_content)
                sentences = [s.strip() for s in sentences if s.strip()]
                text_data["sentence_count"] = len(sentences)
                
                # Average words per sentence
                if text_data["sentence_count"] > 0:
                    text_data["avg_words_per_sentence"] = round(
                        text_data["word_count"] / text_data["sentence_count"], 2
                    )
                
                # Paragraph count
                paragraphs = driver.find_elements(By.TAG_NAME, "p")
                text_data["paragraph_count"] = len(paragraphs)
                
                # Top keywords (excluding common words)
                stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
                             'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'be', 'been',
                             'this', 'that', 'these', 'those', 'it', 'its', 'they', 'their'}
                
                filtered_words = [w for w in words if w not in stop_words and len(w) > 3]
                word_freq = Counter(filtered_words)
                text_data["top_keywords"] = [
                    {"word": word, "count": count} 
                    for word, count in word_freq.most_common(10)
                ]
                
                # Simple readability score (Flesch Reading Ease approximation)
                if text_data["word_count"] > 0 and text_data["sentence_count"] > 0:
                    avg_sentence_length = text_data["word_count"] / text_data["sentence_count"]
                    avg_syllables = 1.5  # Rough estimate
                    
                    # Flesch Reading Ease formula
                    readability = 206.835 - (1.015 * avg_sentence_length) - (84.6 * avg_syllables)
                    text_data["readability_score"] = round(max(0, min(100, readability)), 2)
            
            logger.info(f"Text analysis: {text_data['word_count']} words, {text_data['sentence_count']} sentences")
            
        except Exception as e:
            logger.error(f"Error extracting text content: {str(e)}")
        
        return text_data
    
    def compile_report(self, url: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compile all extracted data into a comprehensive report.
        
        Args:
            url: URL that was scraped
            data: Dictionary containing all extracted data
            
        Returns:
            Comprehensive report dictionary
        """
        report = {
            "url": url,
            "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "metadata": data.get("metadata", {}),
            "headings": data.get("headings", {}),
            "images": data.get("images", {}),
            "links": data.get("links", {}),
            "performance": data.get("performance", {}),
            "accessibility": data.get("accessibility", {}),
            "design": data.get("design", {}),
            "text_content": data.get("text_content", {}),
            "summary": {
                "total_issues": 0,
                "critical_issues": [],
                "warnings": []
            }
        }
        
        # Aggregate issues
        all_issues = []
        
        # Collect issues from each category
        if data.get("headings", {}).get("issues"):
            all_issues.extend(data["headings"]["issues"])
        if data.get("images", {}).get("issues"):
            all_issues.extend(data["images"]["issues"])
        if data.get("links", {}).get("issues"):
            all_issues.extend(data["links"]["issues"])
        if data.get("accessibility", {}).get("issues"):
            all_issues.extend(data["accessibility"]["issues"])
        
        report["summary"]["total_issues"] = len(all_issues)
        report["summary"]["critical_issues"] = all_issues[:5]  # Top 5 issues
        
        logger.info(f"Report compiled: {report['summary']['total_issues']} total issues")
        
        return report
    
    def scrape_page(self, url: str) -> Dict[str, Any]:
        """
        Main method to scrape a page and extract all data.
        
        Args:
            url: URL to scrape
            
        Returns:
            Complete scraping report
        """
        try:
            # Load the page
            driver = self.load_page(url)
            
            # Extract all data
            data = {
                "metadata": self.extract_metadata(driver),
                "headings": self.extract_headings(driver),
                "images": self.extract_images(driver),
                "links": self.extract_links(driver, url),
                "performance": self.extract_performance_metrics(driver),
                "accessibility": self.extract_accessibility(driver),
                "design": self.extract_design_signals(driver),
                "text_content": self.extract_text_content(driver)
            }
            
            # Compile final report
            report = self.compile_report(url, data)
            
            return report
            
        except Exception as e:
            logger.error(f"Error scraping page {url}: {str(e)}")
            raise
        
        finally:
            # Clean up
            if self.driver:
                try:
                    self.driver.quit()
                except Exception as e:
                    logger.error(f"Error closing driver: {str(e)}")
    
    def scrape_multiple_pages(self, urls: List[str]) -> List[Dict[str, Any]]:
        """
        Scrape multiple pages.
        
        Args:
            urls: List of URLs to scrape
            
        Returns:
            List of scraping reports
        """
        reports = []
        
        for url in urls:
            try:
                report = self.scrape_page(url)
                reports.append(report)
            except Exception as e:
                logger.error(f"Failed to scrape {url}: {str(e)}")
                reports.append({
                    "url": url,
                    "error": str(e),
                    "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S")
                })
        
        return reports
