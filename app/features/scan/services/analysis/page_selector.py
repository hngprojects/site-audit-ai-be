import os
import re
import logging
import json
from typing import List, Dict, Any
from openai import OpenAI

from app.platform.config import settings

logger = logging.getLogger(__name__)

# Load prompt template from utils
PROMPT_PATH = os.path.join(
    os.path.dirname(__file__), "../utils/PROMPT.md"
)


def load_prompt_template():
    """Load the prompt template from PROMPT.md file. Might tweak later"""
    with open(PROMPT_PATH, "r") as f:
        return f.read()


class PageSelectorService:
    """Service for intelligently selecting important pages for website audit."""
    
    # URL pattern for extraction - matches http/https URLs
    URL_PATTERN = re.compile(r'https?://[^\s<>"\']+')
    
    @staticmethod
    def filter_important_pages(
        pages: List[str],
        top_n: int = 5,
        referer: str = "",
        site_title: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Select important pages from a list using LLM with structured metadata.
        Args:
            pages: List of discovered page URLs
            top_n: Maximum number of pages to select
            referer: HTTP referer for API call
            site_title: Site title for API call
            
        Returns:
            List of dicts with title, url, description, priority
        """
        if not pages:
            logger.info("No pages provided for selection")
            return []
        
        # Cap at actual available pages
        actual_max = min(top_n, len(pages))
        
        # If very few pages, skip LLM call and return all with default metadata
        if len(pages) <= 7:
            logger.info(f"Only {len(pages)} pages found, returning all without LLM")
            return PageSelectorService._create_default_selection(pages)
        
        try:
            selected = PageSelectorService._select_via_llm(
                pages=pages,
                max_pages=actual_max,
                referer=referer,
                site_title=site_title
            )
            
            # Validate and filter results
            selected = PageSelectorService._validate_structured_selection(
                selected=selected,
                original_pages=pages,
                max_pages=actual_max
            )
            
            logger.info(f"LLM selected {len(selected)} pages from {len(pages)} discovered")
            return selected
            
        except Exception as e:
            logger.error(f"LLM selection failed: {e}, falling back to heuristic")
            return PageSelectorService._fallback_structured_selection(pages, actual_max)
    
    @staticmethod
    def _select_via_llm(
        pages: List[str],
        max_pages: int,
        referer: str,
        site_title: str
    ) -> List[Dict[str, Any]]:
        """Call LLM to select important pages with structured output."""
        # Prepare prompt
        prompt_template = load_prompt_template()
        prompt = prompt_template.format(
            top_n=max_pages,
            urls="\n".join(pages)
        )
        
        # Call OpenRouter API
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.OPENROUTER_API_KEY
        )
        
        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": referer,
                "X-Title": site_title,
            },
            extra_body={},
            model="z-ai/glm-4.5-air:free",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        
        text = completion.choices[0].message.content or ""
        
        # Try to parse as JSON first
        try:
            # Clean markdown code blocks if present
            cleaned_text = text.strip()
            if cleaned_text.startswith('```'):
                cleaned_text = '\n'.join(cleaned_text.split('\n')[1:-1])
            
            result = json.loads(cleaned_text)
            
            # Validate structure
            if isinstance(result, list):
                return result
            else:
                logger.warning("LLM returned non-list JSON, falling back to parsing")
        except json.JSONDecodeError:
            logger.warning("LLM response not valid JSON, attempting to parse")
        
        # Fallback: try to extract URLs and create basic structure
        found_urls = PageSelectorService.URL_PATTERN.findall(text)
        return [
            {
                "title": PageSelectorService._extract_title_from_url(url),
                "url": url,
                "description": "Selected for comprehensive audit",
                "priority": "medium"
            }
            for url in found_urls
        ]
    
    @staticmethod
    def _validate_structured_selection(
        selected: List[Dict[str, Any]],
        original_pages: List[str],
        max_pages: int
    ) -> List[Dict[str, Any]]:
        """Validate and clean up LLM structured selection."""
        original_normalized = {url.rstrip('/').lower() for url in original_pages}
        original_map = {url.rstrip('/').lower(): url for url in original_pages}
        
        validated = []
        seen = set()
        
        for item in selected:
            if not isinstance(item, dict):
                continue
                
            url = item.get('url', '').strip().rstrip('/')
            url_lower = url.lower()
            
            # Check if URL is from original list
            if url_lower in original_normalized and url_lower not in seen:
                validated.append({
                    "title": item.get('title', PageSelectorService._extract_title_from_url(url)),
                    "url": original_map[url_lower],
                    "description": item.get('description', 'Selected for audit'),
                    "priority": item.get('priority', 'medium')
                })
                seen.add(url_lower)
        
        # Respect max limit
        return validated[:max_pages]
    
    @staticmethod
    def _create_default_selection(pages: List[str]) -> List[Dict[str, Any]]:
        """Create default selection for small page lists."""
        return [
            {
                "title": PageSelectorService._extract_title_from_url(url),
                "url": url,
                "description": "Selected for comprehensive audit",
                "priority": "high" if i == 0 else "medium"
            }
            for i, url in enumerate(pages)
        ]
    
    @staticmethod
    def _fallback_structured_selection(pages: List[str], max_pages: int) -> List[Dict[str, Any]]:
        """Heuristic fallback with structured output."""
        # Priority keywords for important pages
        priority_keywords = [
            'home', 'index', 'about', 'contact', 'service', 'product',
            'pricing', 'faq', 'blog', 'privacy', 'terms', 'team',
            'portfolio', 'work', 'case', 'testimonial', 'feature'
        ]
        
        # Skip keywords for less important pages
        skip_keywords = [
            'login', 'logout', 'signup', 'register', 'cart', 'checkout',
            'search', 'page=', 'sort=', 'filter=', 'session', 'token'
        ]
        
        scored = []
        for url in pages:
            url_lower = url.lower()
            
            if any(kw in url_lower for kw in skip_keywords):
                continue
            
            score = sum(1 for kw in priority_keywords if kw in url_lower)
            
            if url.rstrip('/').count('/') <= 3:
                score += 2
            
            scored.append((score, url))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        
        return [
            {
                "title": PageSelectorService._extract_title_from_url(url),
                "url": url,
                "description": "Selected based on URL importance heuristics",
                "priority": "high" if score >= 3 else ("medium" if score >= 1 else "low")
            }
            for score, url in scored[:max_pages]
        ]
    
    @staticmethod
    def _extract_title_from_url(url: str) -> str:
        """Extract a human-readable title from URL."""
        from urllib.parse import urlparse
        
        parsed = urlparse(url)
        path = parsed.path.strip('/').split('/')[-1] or 'Homepage'
        
        # Clean up the path
        title = path.replace('-', ' ').replace('_', ' ').title()
        return title if title else 'Homepage'
