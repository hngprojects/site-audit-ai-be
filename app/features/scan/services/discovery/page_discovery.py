import re
import logging
from typing import List, Set
from urllib.parse import urlparse, urljoin

import httpx
from bs4 import BeautifulSoup
from openai import OpenAI

from app.platform.config import settings

logger = logging.getLogger(__name__)


class PageDiscoveryService:
    """Service for discovering important pages from a website using LLM."""

    # URL pattern for extraction - matches http/https URLs (used only as backup)
    URL_PATTERN = re.compile(r'https?://[^\s<>"\']+')

    @staticmethod
    def discover_pages(url: str, max_pages: int = 10) -> List[str]:
        """
        Discover important pages from a website using LLM.

        Args:
            url: The base URL of the website to discover pages from
            max_pages: Maximum number of pages to discover (default: 10)

        Returns:
            List of discovered page URLs
        """
        base_url = PageDiscoveryService._normalize_url(url)

        try:
            # 1. Collect real candidate URLs from the site
            candidate_urls = PageDiscoveryService._collect_candidate_urls(
                base_url, max_candidates=100
            )

            if not candidate_urls:
                logger.warning(f"No candidate URLs found for {base_url}, falling back to homepage only")
                return [base_url]

            # 2. Ask LLM to rank/choose from those URLs
            ranked_pages = PageDiscoveryService._rank_pages_via_llm(
                base_url=base_url,
                candidate_urls=candidate_urls,
                max_pages=max_pages,
            )

            # 3. Ensure homepage is included
            if base_url not in ranked_pages:
                ranked_pages.insert(0, base_url)

            # 4. Limit to max_pages & dedupe while preserving order
            seen: Set[str] = set()
            result: List[str] = []
            for p in ranked_pages:
                p_norm = PageDiscoveryService._normalize_url(p)
                if p_norm not in seen:
                    seen.add(p_norm)
                    result.append(p_norm)
                if len(result) >= max_pages:
                    break

            logger.info(f"LLM discovered {len(result)} pages for {base_url}")
            return result

        except Exception as e:
            logger.error(f"LLM discovery failed: {e}, falling back to homepage only", exc_info=True)
            return [base_url]

    # -------------------------------------------------------------------------
    # URL collection (real data from the site)
    # -------------------------------------------------------------------------

    @staticmethod
    def _collect_candidate_urls(base_url: str, max_candidates: int = 100) -> List[str]:
        """
        Collect candidate URLs from the website:
        - sitemap.xml (if present)
        - links on the homepage

        Returns a list of unique, same-domain URLs.
        """
        urls: Set[str] = set()
        urls.add(base_url)

        parsed_base = urlparse(base_url)
        base_domain = parsed_base.netloc

        def add_url(u: str):
            u = PageDiscoveryService._normalize_url(u)
            if not u:
                return
            parsed = urlparse(u)
            # Only keep same domain
            if parsed.netloc == base_domain:
                urls.add(u)

        # HTTP client
        with httpx.Client(follow_redirects=True, timeout=10) as client:
            # 1) Try sitemap.xml
            sitemap_candidates = [
                urljoin(base_url + "/", "sitemap.xml"),
                urljoin(base_url + "/", "sitemap_index.xml"),
            ]

            for sitemap_url in sitemap_candidates:
                if len(urls) >= max_candidates:
                    break
                try:
                    r = client.get(sitemap_url)
                    if r.status_code == 200 and "<urlset" in r.text:
                        # naive extract of <loc> tags
                        for loc in re.findall(r"<loc>(.*?)</loc>", r.text):
                            add_url(loc.strip())
                            if len(urls) >= max_candidates:
                                break
                except Exception as e:
                    logger.debug(f"Failed to fetch sitemap {sitemap_url}: {e}")

            # 2) Homepage links
            if len(urls) < max_candidates:
                try:
                    r = client.get(base_url)
                    if r.status_code == 200:
                        soup = BeautifulSoup(r.text, "html.parser")
                        for a in soup.find_all("a", href=True):
                            href = a["href"]
                            full = urljoin(base_url + "/", href)
                            # Remove fragments
                            full = full.split("#")[0]
                            add_url(full)
                            if len(urls) >= max_candidates:
                                break
                except Exception as e:
                    logger.debug(f"Failed to fetch homepage {base_url}: {e}")

        return list(urls)[:max_candidates]

    # -------------------------------------------------------------------------
    # LLM ranking (choose from candidate URLs only)
    # -------------------------------------------------------------------------

    @staticmethod
    def _rank_pages_via_llm(base_url: str, candidate_urls: List[str], max_pages: int) -> List[str]:
        """
        Call LLM to rank/choose the most important pages from a list of URLs.

        The LLM MUST NOT invent new URLs; it must choose only from candidate_urls.
        """
        if not settings.OPENROUTER_API_KEY:
            raise ValueError(
                "OPENROUTER_API_KEY is not set. "
                "Please set it as an environment variable: $env:OPENROUTER_API_KEY='your-key-here'"
            )

        # Build the list of candidate URLs for the prompt
        urls_block = "\n".join(candidate_urls)

        prompt = f"""You are analyzing the website: {base_url}

You are given a list of URLs that are confirmed to exist on this website:

{urls_block}

Your task: choose up to {max_pages} of the MOST IMPORTANT pages
for an audit (SEO, UX, performance, conversions, accessibility, etc.).

RULES:
- You MUST ONLY choose URLs from the list above.
- Do NOT invent or modify URLs.
- Prioritize pages that are important for visitors and the business:
  - Homepage
  - About / Company
  - Products / Services / Pricing
  - Contact
  - Blog / Resources (if present)
  - Key landing pages
- Return ONE URL per line.
- No explanations, no numbering, no extra text.

Output format example:
{base_url}
{base_url}/about
{base_url}/products
"""

        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.OPENROUTER_API_KEY,
        )

        completion = client.chat.completions.create(
            model="z-ai/glm-4.5-air:free",
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            temperature=0.0,  # deterministic, no creativity for URLs
        )

        raw_text = completion.choices[0].message.content or ""
        logger.debug(f"LLM raw page discovery output for {base_url}:\n{raw_text}")

        # Parse LLM output: one URL per line
        candidate_set = {PageDiscoveryService._normalize_url(u) for u in candidate_urls}
        selected: List[str] = []

        for line in raw_text.splitlines():
            line = line.strip()
            if not line or not line.startswith("http"):
                continue
            url_norm = PageDiscoveryService._normalize_url(line)
            if url_norm in candidate_set and url_norm not in selected:
                selected.append(url_norm)

        # Fallback: if LLM output is useless, fall back to simple heuristics
        if not selected:
            logger.warning(f"LLM returned no valid URLs for {base_url}, falling back to heuristic selection")
            selected = PageDiscoveryService._heuristic_rank(base_url, candidate_urls, max_pages)

        return selected

    # -------------------------------------------------------------------------
    # Heuristic fallback
    # -------------------------------------------------------------------------

    @staticmethod
    def _heuristic_rank(base_url: str, candidate_urls: List[str], max_pages: int) -> List[str]:
        """
        Fallback heuristic ranking when LLM result is empty or invalid.
        Tries to pick "obvious" important pages by path patterns.
        """
        base_norm = PageDiscoveryService._normalize_url(base_url)
        urls_norm = [PageDiscoveryService._normalize_url(u) for u in candidate_urls]

        # Always start with homepage if present
        ranked: List[str] = []
        if base_norm in urls_norm:
            ranked.append(base_norm)

        # Simple priority by common patterns
        priority_patterns = [
            "about",
            "contact",
            "services",
            "service",
            "products",
            "pricing",
            "blog",
            "news",
            "support",
            "help",
        ]

        def score(u: str) -> int:
            path = urlparse(u).path.lower()
            s = 0
            for p in priority_patterns:
                if p in path:
                    s += 1
            return s

        # Sort remaining URLs by heuristic score (desc) then by length (shorter first)
        remaining = [u for u in urls_norm if u != base_norm]
        remaining_sorted = sorted(
            remaining,
            key=lambda u: (score(u), -len(u)),
            reverse=True,
        )

        for u in remaining_sorted:
            if u not in ranked:
                ranked.append(u)
            if len(ranked) >= max_pages:
                break

        return ranked

    # -------------------------------------------------------------------------
    # Utility
    # -------------------------------------------------------------------------

    @staticmethod
    def _normalize_url(url: str) -> str:
        """Normalize URL by stripping whitespace and trailing slash."""
        if not url:
            return ""
        return url.strip().rstrip("/")
