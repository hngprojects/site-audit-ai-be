import os
import re
import logging
from typing import List
from openai import OpenAI
import google.generativeai as genai

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
    ) -> List[str]:
        """
        Select important pages from a list using LLM.
        Args:
            pages: List of discovered page URLs
            top_n: Maximum number of pages to select
            referer: HTTP referer for API call
            site_title: Site title for API call
            
        Returns:
            List of selected important page URLs
        """
        if not pages:
            logger.info("No pages provided for selection")
            return []
        
        # Cap at actual available pages
        actual_max = min(top_n, len(pages))
        
        # If very few pages, skip LLM call and return all
        if len(pages) <= 7:
            logger.info(f"Only {len(pages)} pages found, returning all without LLM")
            return pages
        
        try:
            selected = PageSelectorService._select_via_llm(
                pages=pages,
                max_pages=actual_max,
                referer=referer,
                site_title=site_title
            )
            
            # Validate and filter results
            selected = PageSelectorService._validate_selection(
                selected=selected,
                original_pages=pages,
                max_pages=actual_max
            )
            
            logger.info(f"LLM selected {len(selected)} pages from {len(pages)} discovered")
            return selected
            
        except Exception as e:
            logger.error(f"LLM selection failed: {e}, falling back to heuristic")
            return PageSelectorService._fallback_selection(pages, actual_max)
    
    @staticmethod
    def _select_via_llm(
        pages: List[str],
        max_pages: int,
        referer: str,
        site_title: str
    ) -> List[str]:
        """Call LLM to select important pages."""
        # Configure Gemini API
        genai.configure(api_key=settings.GOOGLE_GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash-lite') 
        
        # Prepare prompt
        prompt_template = load_prompt_template()
        prompt = prompt_template.format(
            top_n=max_pages,
            urls="\n".join(pages)
        )
        
        # Call Gemini API
        response = model.generate_content(prompt)
        text = response.text
        
        # ===== OLD OpenRouter Implementation (Commented Out) =====
        # client = OpenAI(
        #     base_url="https://openrouter.ai/api/v1",
        #     api_key=settings.OPENROUTER_API_KEY
        # )
        # 
        # completion = client.chat.completions.create(
        #     extra_headers={
        #         "HTTP-Referer": referer,
        #         "X-Title": site_title,
        #     },
        #     extra_body={},
        #     model="z-ai/glm-4.5-air:free",
        #     messages=[
        #         {
        #             "role": "user",
        #             "content": prompt
        #         }
        #     ]
        # )
        # 
        # text = completion.choices[0].message.content or ""
        # =========================================================
        
        # Extract URLs from response using regex (more robust than line splitting)
        found_urls = PageSelectorService.URL_PATTERN.findall(text)
        
        # Also try line-by-line for cleaner responses
        for line in text.splitlines():
            line = line.strip()
            # Remove common prefixes like "1.", "- ", "* "
            line = re.sub(r'^[\d]+[.\)]\s*', '', line)
            line = re.sub(r'^[-*•]\s*', '', line)
            line = line.strip()
            
            if line.startswith('http') and line not in found_urls:
                found_urls.append(line)
        
        return found_urls
    
    @staticmethod
    def _validate_selection(
        selected: List[str],
        original_pages: List[str],
        max_pages: int
    ) -> List[str]:
        """Validate and clean up LLM selection."""
        # Normalize original pages for comparison
        original_normalized = {url.rstrip('/').lower() for url in original_pages}
        original_map = {url.rstrip('/').lower(): url for url in original_pages}
        
        validated = []
        seen = set()
        
        for url in selected:
            # Clean the URL
            url = url.strip().rstrip('/')
            url_lower = url.lower()
            
            # Check if it's from original list (or close match)
            if url_lower in original_normalized and url_lower not in seen:
                validated.append(original_map[url_lower])
                seen.add(url_lower)
            elif url in original_pages and url.rstrip('/').lower() not in seen:
                validated.append(url)
                seen.add(url.rstrip('/').lower())
        
        # Respect max limit
        return validated[:max_pages]
    
    @staticmethod
    def _fallback_selection(pages: List[str], max_pages: int) -> List[str]:
        """Heuristic fallback when LLM fails."""
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
            
            # Skip if contains skip keywords
            if any(kw in url_lower for kw in skip_keywords):
                continue
            
            # Score based on priority keywords
            score = sum(1 for kw in priority_keywords if kw in url_lower)
            
            # Boost root/homepage
            if url.rstrip('/').count('/') <= 3:
                score += 2
            
            scored.append((score, url))
        
        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)
        
        return [url for _, url in scored[:max_pages]]
