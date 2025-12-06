import os
import logging
import tempfile
import json
from typing import List, Dict
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from openai import OpenAI
from app.platform.config import settings

_CHROMEDRIVER_PATH = None

logger = logging.getLogger(__name__)

class PageDiscoveryService:
    
    @staticmethod
    def discover_pages(url: str, max_pages: int = 10) -> List[str]:
        """
        Discover pages from a website using Selenium.
        
        Args:
            url: Base URL to start discovery from
            max_pages: Maximum number of pages to discover (default: 10)
            
        Returns:
            List of discovered URLs (all from same base domain)
        """
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
            # Parse base URL for domain validation
            base_parsed = urlparse(url)
            base_domain = f"{base_parsed.scheme}://{base_parsed.netloc}"
            
            driver.get(url)
            visited = set()
            to_visit = [url]
            pages = []

            while to_visit and len(visited) < max_pages:
                current = to_visit.pop(0)  # Use BFS (pop from front)
                if current in visited:
                    continue
                visited.add(current)
                
                try:
                    driver.get(current)
                    pages.append(current)
                    
                    links = driver.find_elements(By.TAG_NAME, "a")
                    for link in links:
                        href = link.get_attribute("href")
                        if href and PageDiscoveryService._is_same_domain(href, base_domain):
                            if href not in visited and href not in to_visit:
                                to_visit.append(href)
                except Exception as e:
                    logger.warning(f"Failed to load page {current}: {e}")
                    continue
                    
            logger.info(f"Discovered {len(pages)} pages from {url}")
            return pages
        finally:
            driver.quit()

    @staticmethod        
    def fallback_selection(pages: List[str], max_pages: int) -> List[Dict[str, str]]:
        """Heuristic fallback when LLM fails. Returns detailed page metadata."""
        priority_keywords = [
            'home', 'index', 'about', 'contact', 'service', 'product',
            'pricing', 'faq', 'blog', 'privacy', 'terms', 'team',
            'portfolio', 'work', 'case', 'testimonial', 'feature'
        ]
        skip_keywords = [
            'login', 'logout', 'signup', 'register', 'cart', 'checkout',
            'search', 'page=', 'sort=', 'filter=', 'session', 'token'
        ]
        scored = []
        for url in pages:
            url_lower = url.lower()
            # Skip URLs with skip keywords
            if any(kw in url_lower for kw in skip_keywords):
                continue
            # Score based on keyword matches
            matched_keywords = [kw for kw in priority_keywords if kw in url_lower]
            score = len(matched_keywords)
            # Boost if likely homepage or top-level page
            if url.rstrip('/').count('/') <= 3:
                score += 2
            # Extract title from last part of URL
            parts = url.rstrip('/').split('/')
            slug = parts[-1] if parts[-1] else parts[-2]
            title = slug.replace('-', ' ').replace('_', ' ').title()
            title = title.split('?')[0] 
            # Choose description
            if matched_keywords:
                desc_source = matched_keywords[0]
            else:
                desc_source = slug or "general site content"
            description = f"A page related to {desc_source.replace('-', ' ').replace('_', ' ')}."
            # Determine priority label
            priority = "high" if matched_keywords else "low"
            scored.append({
                "url": url,
                "title": title or "Untitled Page",
                "description": description,
                "priority": priority,
                "score": score
            })
        # Sort by score descending
        scored.sort(key=lambda x: x["score"], reverse=True)
        # Limit and drop score field before returning
        return [
            {k: v for k, v in item.items() if k != "score"}
            for item in scored[:max_pages]
        ]
    
    @staticmethod
    def _is_same_domain(url: str, base_domain: str) -> bool:
        """
        Check if URL belongs to the same domain as base.
        
        Args:
            url: URL to check
            base_domain: Base domain (e.g., "https://example.com")
            
        Returns:
            True if URL is from same domain, False otherwise
        """
        try:
            parsed = urlparse(url)
            # Ensure URL has a valid scheme and netloc
            if not parsed.scheme or not parsed.netloc:
                return False
            url_domain = f"{parsed.scheme}://{parsed.netloc}"
            return url_domain == base_domain
        except Exception:
            return False
    
    @staticmethod
    def rank_and_annotate_pages(base_url: str, urls: List[str], max_pages: int = 10) -> List[Dict]:
        """
        Use LLM to rank pages by importance and generate metadata (title, description, priority).
        
        Args:
            base_url: The base URL of the website
            urls: List of discovered URLs to rank and annotate
            max_pages: Maximum number of pages to return (default: 10)
            
        Returns:
            List of dictionaries with keys: title, url, priority, description
        """
        if not urls:
            return []
        
        # Limit URLs to process
        urls_to_process = urls[:20]  # Process up to 20, return top 10
        
        if not settings.OPENROUTER_API_KEY:
            raise ValueError(
                "OPENROUTER_API_KEY is not set. Please set OPENROUTER_API_KEY environment variable."
            )
        
        try:
            client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=settings.OPENROUTER_API_KEY,
            )
            
            urls_list = "\n".join([f"{idx + 1}. {url}" for idx, url in enumerate(urls_to_process)])
            
            prompt = f"""You are analyzing URLs discovered from the website {base_url} using web crawling.

These are the actual URLs found on the website:
{urls_list}

Your task:
1. Analyze each URL's path and structure to understand what the page is about
2. Rank them by importance for a website audit (SEO, UX, performance, conversions)
3. Generate meaningful metadata for each page

For each URL, analyze:
- The URL path structure (e.g., /shop/products, /blog/article, /contact)
- Common patterns (e.g., /checkout, /cart, /about, /services)
- The likely purpose and content of the page

Then provide:
1. **Title**: A short, descriptive title (2-5 words, capitalize first letter) based on the URL path
   - Example: "https://example.com/shop/products" → "Shop Products"
   - Example: "https://example.com/about-us" → "About Us"
   - Example: "https://example.com/contact" → "Contact"

2. **Priority**: "High Priority", "Medium Priority", or "Low Priority"
   - High Priority: Homepage, product/service pages, checkout/cart, contact, key landing pages
   - Medium Priority: About, blog, support, help, documentation
   - Low Priority: Legal, privacy policy, terms, sitemap, archives, admin pages

3. **Description**: A meaningful, contextual description (1 sentence, max 80 characters) that explains:
   - What the page is for
   - Why it's important for customers or the business
   - What users would expect to find there
   
   Make descriptions specific and helpful, like:
   - "Your main landing page, and the first impression customers get of your brand"
   - "Where customers browse and buy your products"
   - "This page tells visitors about your company, mission, and team"
   - "Where customers review their items and complete their purchase"
   - "Helps customers reach your business"

Return ONLY a valid JSON array with this exact structure:
[
  {{
    "url": "https://example.com",
    "title": "Home",
    "priority": "High Priority",
    "description": "Your main landing page, and the first impression customers get of your brand"
  }},
  {{
    "url": "https://example.com/shop",
    "title": "Shop",
    "priority": "High Priority",
    "description": "Where customers browse and buy your products"
  }}
]

IMPORTANT:
- Return the top {max_pages} most important pages, ranked from most to least important
- Only include URLs from the list above
- Base titles and descriptions on the actual URL paths - be specific and meaningful
- Return valid JSON only, no other text or explanations"""

            # Try LLM call with retry logic for rate limits
            max_retries = 3
            retry_delay = 1  # Start with 1 second
            raw_text = ""
            completion = None
            
            for attempt in range(max_retries):
                try:
                    completion = client.chat.completions.create(
                        model="deepseek/deepseek-chat-v3-0324",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.2,
                        response_format={"type": "json_object"} if hasattr(client.chat.completions.create, "response_format") else None,
                    )
                    
                    raw_text = completion.choices[0].message.content or ""
                    if raw_text:
                        logger.info(f"✅ LLM successfully annotated {len(urls_to_process)} URLs")
                        logger.debug(f"LLM annotation output: {raw_text}")
                        break  # Success, exit retry loop
                    else:
                        raise Exception("LLM returned empty response")
                    
                except Exception as api_error:
                    error_str = str(api_error).lower()
                    is_rate_limit = "429" in error_str or "rate limit" in error_str
                    
                    if is_rate_limit and attempt < max_retries - 1:
                        wait_time = retry_delay * (2 ** attempt)  # Exponential backoff: 1s, 2s, 4s
                        logger.warning(
                            f"⚠️ OpenRouter rate limit hit (attempt {attempt + 1}/{max_retries}). "
                            f"Retrying in {wait_time} seconds..."
                        )
                        import time
                        time.sleep(wait_time)
                        continue
                    else:
                        # Final attempt failed or non-rate-limit error
                        raise api_error
            
            if not raw_text:
                raise Exception("LLM returned empty response after retries")
            
            # Try to parse JSON response
            try:
                # Clean up response - might have markdown code blocks or extra text
                if "```json" in raw_text:
                    raw_text = raw_text.split("```json")[1].split("```")[0].strip()
                elif "```" in raw_text:
                    raw_text = raw_text.split("```")[1].split("```")[0].strip()
                
                # Remove any leading/trailing non-JSON text
                start_idx = raw_text.find("[")
                end_idx = raw_text.rfind("]") + 1
                if start_idx != -1 and end_idx > start_idx:
                    raw_text = raw_text[start_idx:end_idx]
                
                # Parse JSON
                pages = json.loads(raw_text)
                if not isinstance(pages, list):
                    pages = [pages]
                
                # Validate and format results
                result = []
                for page in pages[:max_pages]:
                    if isinstance(page, dict) and "url" in page:
                        result.append({
                            "title": page.get("title", "Page"),
                            "url": page.get("url", ""),
                            "priority": page.get("priority", "Medium Priority"),
                            "description": page.get("description", "A page on this website")
                        })
                
                if result:
                    logger.info(f"✅ Successfully annotated {len(result)} pages with LLM (OpenRouter)")
                    return result
                else:
                    raise Exception("LLM returned empty result after parsing")
                    
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM JSON response: {e}")
                logger.debug(f"Raw response: {raw_text}")
                raise Exception(f"Failed to parse LLM JSON response: {e}")
        
        except Exception as e:
            error_str = str(e).lower()
            if "429" in error_str or "rate limit" in error_str:
                logger.error(
                    f"❌ OpenRouter rate limit exceeded after {max_retries} retries. "
                    f"Free tier limit: 50 requests/day. "
                    f"Solutions: 1) Wait for daily reset, 2) Add credits to OpenRouter for higher limits."
                )
                raise Exception(
                    "OpenRouter rate limit exceeded. Please wait for daily reset or add credits to OpenRouter."
                )
            else:
                logger.error(f"❌ OpenRouter LLM annotation failed: {e}")
                raise Exception(f"LLM annotation failed: {e}")
    