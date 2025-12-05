import logging
import re
from collections import deque
from typing import List, Set
from urllib.parse import urlparse, urljoin

import httpx
from bs4 import BeautifulSoup
from openai import OpenAI

from app.platform.config import settings

logger = logging.getLogger(__name__)


class PageDiscoveryService:
    """Service for discovering important pages from a website using crawling + LLM ranking."""

    # URL pattern (used only in a couple of places if needed)
    URL_PATTERN = re.compile(r"https?://[^\s<>'\"]+")

    # How far to crawl
    MAX_CANDIDATES = 15
    MAX_DEPTH = 2

    @staticmethod
    def discover_pages(url: str, max_pages: int = 10) -> List[str]:
        """
        Discover important pages from a website using:
        1. Real URL discovery (sitemap + BFS crawl)
        2. LLM ranking from those URLs
        3. Optional LLM guessing + HTTP verification for sparse sites
        4. Heuristic fallback

        Args:
            url: The base URL of the website to discover pages from
            max_pages: Maximum number of pages to discover

        Returns:
            List of discovered page URLs (normalized, same domain, deduped)
        """
        base_url = PageDiscoveryService._normalize_url(url)

        try:
            # 1. Collect real candidate URLs from the site
            candidate_urls = PageDiscoveryService._collect_candidate_urls(
                base_url,
                max_candidates=PageDiscoveryService.MAX_CANDIDATES,
                max_depth=PageDiscoveryService.MAX_DEPTH,
            )

            # 2. For very sparse sites, let the LLM "guess" URLs and verify them
            # Only do this if we have very few URLs (1-2), and limit guesses
            if len(candidate_urls) <= 2:
                logger.info(
                    f"Only {len(candidate_urls)} candidate URLs found for {base_url}; "
                    f"augmenting with conservative guessed + verified URLs"
                )
                guessed = PageDiscoveryService._guess_and_verify_urls(
                    base_url,
                    max_guesses=5,  # Reduced from 10 to be more conservative
                )
                logger.info(f"Guessed and verified {len(guessed)} URLs for {base_url}")
                # Only add verified URLs that we don't already have
                for g in guessed:
                    if g not in candidate_urls:
                        candidate_urls.append(g)
                logger.info(f"Total candidate URLs after guessing: {len(candidate_urls)}")

            # If still nothing, fall back to homepage only
            if not candidate_urls:
                logger.warning(
                    f"No candidate URLs found for {base_url}, falling back to homepage only"
                )
                return [base_url]

            # 3. Decide whether to use LLM ranking or heuristic only
            logger.info(f"Ranking {len(candidate_urls)} candidate URLs for {base_url}")
            if len(candidate_urls) <= 3:
                logger.info(
                    f"Very few candidates ({len(candidate_urls)}) for {base_url}, "
                    f"using heuristic ranking only"
                )
                ranked_pages = PageDiscoveryService._heuristic_rank(
                    base_url, candidate_urls, max_pages
                )
                logger.info(f"Heuristic ranking returned {len(ranked_pages)} pages")
            else:
                ranked_pages = PageDiscoveryService._rank_pages_via_llm(
                    base_url=base_url,
                    candidate_urls=candidate_urls,
                    max_pages=max_pages,
                )
                logger.info(f"LLM ranking returned {len(ranked_pages)} pages")

            # 4. Ensure homepage is included
            if base_url not in ranked_pages:
                ranked_pages.insert(0, base_url)

            # 5. Dedupe while preserving order + limit to max_pages
            seen: Set[str] = set()
            result: List[str] = []
            for p in ranked_pages:
                p_norm = PageDiscoveryService._normalize_url(p)
                if p_norm and p_norm not in seen:
                    seen.add(p_norm)
                    result.append(p_norm)
                if len(result) >= max_pages:
                    break

            # 6. Final verification: ensure all returned pages actually exist (status 200)
            verified_result = PageDiscoveryService._verify_urls_exist(result, base_url)
            
            logger.info(f"Discovered {len(verified_result)} verified pages (out of {len(result)} candidates) for {base_url}")
            return verified_result

        except Exception as e:
            logger.error(
                f"Page discovery failed for {base_url}: {e}. Falling back to homepage only",
                exc_info=True,
            )
            return [base_url]

    # -------------------------------------------------------------------------
    # URL collection (sitemap + BFS crawl)
    # -------------------------------------------------------------------------

    @staticmethod
    def _collect_candidate_urls(
        base_url: str,
        max_candidates: int = 100,
        max_depth: int = 2,
    ) -> List[str]:
        """
        Collect candidate URLs from the website:
        - sitemap.xml / sitemap_index.xml (if present)
        - breadth-first crawl up to max_depth from the base_url

        Only keeps same-domain, normalized URLs.
        """
        urls: Set[str] = set()
        base_url = PageDiscoveryService._normalize_url(base_url)
        urls.add(base_url)

        parsed_base = urlparse(base_url)
        base_domain = parsed_base.netloc

        def add_url(u: str):
            u = PageDiscoveryService._normalize_url(u)
            if not u:
                return
            parsed = urlparse(u)
            if parsed.netloc == base_domain:
                urls.add(u)

        with httpx.Client(follow_redirects=True, timeout=10) as client:
            # 1) Try sitemaps
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
                        sitemap_urls = re.findall(r"<loc>(.*?)</loc>", r.text)
                        # Verify sitemap URLs exist before adding them
                        for loc in sitemap_urls:
                            if len(urls) >= max_candidates:
                                break
                            url_to_check = loc.strip()
                            # Quick verification: try HEAD request
                            try:
                                check_r = client.head(url_to_check, timeout=3)
                                if check_r.status_code == 200:
                                    add_url(url_to_check)
                                elif check_r.status_code in [301, 302, 303, 307, 308]:
                                    # Redirects are OK, add the URL
                                    add_url(url_to_check)
                                # Skip 404s and other errors
                            except Exception:
                                # If HEAD fails, try GET as fallback
                                try:
                                    check_r = client.get(url_to_check, timeout=3)
                                    if check_r.status_code == 200:
                                        add_url(url_to_check)
                                except Exception:
                                    # Skip URLs that fail verification
                                    logger.debug(f"Skipping unverifiable sitemap URL: {url_to_check}")
                                    continue
                except Exception as e:
                    logger.debug(f"Failed to fetch sitemap {sitemap_url}: {e}")

            # 2) BFS crawl starting from base_url
            queue = deque()
            visited: Set[str] = set()

            queue.append((base_url, 0))

            while queue and len(urls) < max_candidates:
                current_url, depth = queue.popleft()
                if current_url in visited or depth > max_depth:
                    continue
                visited.add(current_url)

                try:
                    r = client.get(current_url)
                except Exception as e:
                    logger.debug(f"Failed to fetch {current_url}: {e}")
                    continue

                ctype = r.headers.get("content-type", "")
                if r.status_code != 200 or "text/html" not in ctype:
                    continue

                try:
                    soup = BeautifulSoup(r.text, "html.parser")
                except Exception as e:
                    logger.debug(f"Failed to parse HTML for {current_url}: {e}")
                    continue

                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    full = urljoin(current_url + "/", href).split("#")[0]
                    full = PageDiscoveryService._normalize_url(full)

                    if not full:
                        continue

                    parsed = urlparse(full)
                    if parsed.netloc != base_domain:
                        continue

                    if full not in urls:
                        urls.add(full)
                        if depth + 1 <= max_depth:
                            queue.append((full, depth + 1))

                    if len(urls) >= max_candidates:
                        break

        return list(urls)[:max_candidates]

    # -------------------------------------------------------------------------
    # LLM guessing + verification for sparse sites
    # -------------------------------------------------------------------------

    @staticmethod
    def _guess_and_verify_urls(base_url: str, max_guesses: int = 10) -> List[str]:
        """
        Ask the LLM for likely important URLs on the domain, but only keep
        those that actually exist AND are valid HTML pages (not error pages, redirects, etc.).
        """
        base_url = PageDiscoveryService._normalize_url(base_url)
        domain = urlparse(base_url).netloc

        if not settings.OPENROUTER_API_KEY:
            logger.warning("OPENROUTER_API_KEY not set; skipping LLM guess-and-verify")
            return []

        # More conservative prompt - focus on most common pages only
        prompt = f"""
You are analyzing the website: {base_url}

Suggest ONLY the most common and likely-to-exist pages for this website.
Be conservative - only suggest pages that are almost certainly present on most websites.

Focus on these common pages (only if they likely exist):
- Homepage (already have: {base_url})
- /about or /about-us
- /contact
- /products or /services (if it's a business site)
- /blog or /news (if it's a content site)

RULES:
- Use only this exact domain: {domain}
- Return FULL URLs starting with {base_url}
- Return ONE URL per line.
- Do NOT include explanations, numbering, or any extra text.
- Do NOT include URLs from other domains.
- Be conservative - only suggest 3-5 most common pages.
- Do NOT suggest unlikely paths like /admin, /login, /dashboard, etc.
"""

        try:
            client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=settings.OPENROUTER_API_KEY,
            )

            try:
                completion = client.chat.completions.create(
                    model="tngtech/deepseek-r1t2-chimera:free",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,  # Lower temperature for more conservative generation
                )
            except Exception as api_error:
                error_str = str(api_error).lower()
                if "429" in error_str or "rate limit" in error_str:
                    logger.warning(
                        f"OpenRouter rate limit exceeded during guess-and-verify for {base_url}. "
                        f"Skipping LLM guessing."
                    )
                else:
                    logger.warning(
                        f"LLM guess-and-verify failed for {base_url}: {api_error}. "
                        f"Skipping LLM guessing."
                    )
                return []  # Return empty list if LLM fails

            raw = completion.choices[0].message.content or ""
            logger.debug(f"LLM guess-and-verify raw output for {base_url}:\n{raw}")

            lines = [l.strip() for l in raw.splitlines() if l.strip().startswith("http")]

            # Normalize & same-domain filter
            urls: List[str] = []
            for line in lines:
                u = PageDiscoveryService._normalize_url(line)
                if not u:
                    continue
                parsed = urlparse(u)
                if parsed.netloc != domain:
                    continue
                # Skip homepage (already have it)
                if u == base_url:
                    continue
                urls.append(u)

            if not urls:
                return []

            # Stricter verification: must be valid HTML page with actual content
            verified: List[str] = []
            with httpx.Client(follow_redirects=True, timeout=5) as client:
                for u in urls:
                    try:
                        r = client.get(u, follow_redirects=True)
                        
                        # Must be successful status
                        if r.status_code < 200 or r.status_code >= 400:
                            continue
                        
                        # Must be HTML content
                        content_type = r.headers.get("content-type", "").lower()
                        if "text/html" not in content_type:
                            continue
                        
                        # Must have reasonable content length (not empty or error page)
                        # Reduced threshold to be less strict - some pages are legitimately short
                        if len(r.text) < 200:  # Too short, likely error page
                            continue
                        
                        # Check if it's actually HTML (has HTML tags)
                        if "<html" not in r.text.lower() and "<!doctype" not in r.text.lower():
                            continue
                        
                        # Check for common error indicators (but be less strict)
                        # Only check in title/head area, not body content
                        text_lower = r.text.lower()
                        # Check in first 500 chars (head/title area) and last 500 chars
                        head_area = text_lower[:500]
                        error_indicators = ["404", "page not found", "error 404"]
                        # Only reject if error indicator is in title/head AND page is very short
                        if len(r.text) < 1000 and any(indicator in head_area for indicator in error_indicators):
                            # Likely an error page, skip
                            logger.debug(f"Rejected {u} - appears to be error page")
                            continue
                        
                        verified.append(u)
                        logger.debug(f"Verified guessed URL: {u}")
                    except Exception as e:
                        logger.debug(f"Failed to verify guessed URL {u}: {e}")
                        continue

            logger.info(f"Verified {len(verified)} out of {len(urls)} guessed URLs for {base_url}")
            return verified

        except Exception as e:
            logger.error(f"LLM guess-and-verify failed for {base_url}: {e}", exc_info=True)
            return []

    # -------------------------------------------------------------------------
    # LLM ranking from candidate URLs
    # -------------------------------------------------------------------------

    @staticmethod
    def _rank_pages_via_llm(
        base_url: str,
        candidate_urls: List[str],
        max_pages: int,
    ) -> List[str]:
        """
        Call LLM to rank/choose the most important pages from a list of URLs.

        The LLM MUST NOT invent new URLs; it must choose only from candidate_urls.
        """
        base_url = PageDiscoveryService._normalize_url(base_url)

        if not settings.OPENROUTER_API_KEY:
            raise ValueError(
                "OPENROUTER_API_KEY is not set. "
                "Please set it as an environment variable."
            )

        urls_block = "\n".join(candidate_urls)

        prompt = f"""You are analyzing the website: {base_url}

You are given a list of URLs that are confirmed to exist on this website:

{urls_block}

Your task: choose up to {max_pages} of the MOST IMPORTANT pages
for an audit (SEO, UX, performance, accessibility, conversions, etc.).

RULES:
- You MUST ONLY choose URLs from the list above.
- Do NOT invent or modify URLs.
- Prioritize pages that are important for visitors and the business:
  - Homepage
  - About / Company
  - Products / Services / Pricing
  - Contact
  - Blog / Resources / Documentation (if present)
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

        try:
            completion = client.chat.completions.create(
                model="tngtech/deepseek-r1t2-chimera:free",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,  # deterministic, no creativity for URLs
            )

            raw_text = completion.choices[0].message.content or ""
            logger.debug(f"LLM ranking raw output for {base_url}:\n{raw_text}")

            candidate_set = {PageDiscoveryService._normalize_url(u) for u in candidate_urls}
            selected: List[str] = []

            for line in raw_text.splitlines():
                line = line.strip()
                if not line or not line.startswith("http"):
                    continue
                url_norm = PageDiscoveryService._normalize_url(line)
                if url_norm in candidate_set and url_norm not in selected:
                    selected.append(url_norm)

            # Fallback to heuristic if LLM returns nothing valid
            if not selected:
                logger.warning(
                    f"LLM returned no valid URLs for {base_url}, "
                    f"falling back to heuristic ranking"
                )
                selected = PageDiscoveryService._heuristic_rank(
                    base_url, candidate_urls, max_pages
                )

            return selected

        except Exception as e:
            # Handle rate limit errors and other API errors
            error_str = str(e).lower()
            if "429" in error_str or "rate limit" in error_str:
                logger.warning(
                    f"OpenRouter rate limit exceeded for {base_url}. "
                    f"Falling back to heuristic ranking."
                )
            else:
                logger.warning(
                    f"LLM ranking failed for {base_url}: {e}. "
                    f"Falling back to heuristic ranking."
                )
            # Fall back to heuristic ranking when LLM fails
            return PageDiscoveryService._heuristic_rank(
                base_url, candidate_urls, max_pages
            )

    # -------------------------------------------------------------------------
    # Heuristic fallback
    # -------------------------------------------------------------------------

    @staticmethod
    def _heuristic_rank(
        base_url: str,
        candidate_urls: List[str],
        max_pages: int,
    ) -> List[str]:
        """
        Fallback heuristic ranking when LLM result is empty or invalid.
        Tries to pick "obvious" important pages by path patterns.
        """
        base_norm = PageDiscoveryService._normalize_url(base_url)
        urls_norm = [PageDiscoveryService._normalize_url(u) for u in candidate_urls]

        ranked: List[str] = []

        # Always start with homepage if present
        if base_norm in urls_norm:
            ranked.append(base_norm)

        # If we only have homepage, return it (can't rank what we don't have)
        if len(urls_norm) <= 1:
            logger.warning(f"Only homepage in candidate URLs for {base_url}, returning homepage only")
            return ranked[:max_pages]

        priority_patterns = [
            "about",
            "company",
            "team",
            "contact",
            "support",
            "help",
            "services",
            "service",
            "product",
            "products",
            "pricing",
            "plans",
            "blog",
            "news",
            "docs",
            "documentation",
        ]

        def score(u: str) -> int:
            path = urlparse(u).path.lower()
            s = 0
            for p in priority_patterns:
                if p in path:
                    s += 1
            return s

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

        logger.debug(f"Heuristic ranking: {len(ranked)} pages from {len(candidate_urls)} candidates")
        return ranked[:max_pages]

    # -------------------------------------------------------------------------
    # URL Verification
    # -------------------------------------------------------------------------

    @staticmethod
    def _verify_urls_exist(urls: List[str], base_url: str) -> List[str]:
        """
        Verify that all URLs actually exist (return status 200).
        Returns only URLs that successfully return 200.
        """
        if not urls:
            return []
        
        verified: List[str] = []
        base_url_norm = PageDiscoveryService._normalize_url(base_url)
        
        with httpx.Client(follow_redirects=True, timeout=10) as client:
            for url in urls:
                url_norm = PageDiscoveryService._normalize_url(url)
                if not url_norm:
                    continue
                
                try:
                    # Try HEAD first (faster)
                    r = client.head(url_norm, timeout=5)
                    
                    # If HEAD returns 405 (Method Not Allowed), try GET
                    if r.status_code == 405:
                        r = client.get(url_norm, timeout=5)
                    
                    # Only accept 200 status codes
                    if r.status_code == 200:
                        # Double-check it's HTML content
                        content_type = r.headers.get("content-type", "").lower()
                        if "text/html" in content_type or not content_type:
                            verified.append(url_norm)
                            logger.debug(f"Verified URL exists: {url_norm}")
                        else:
                            logger.debug(f"Skipping {url_norm} - not HTML (content-type: {content_type})")
                    else:
                        logger.debug(f"Skipping {url_norm} - status code: {r.status_code}")
                        
                except httpx.TimeoutException:
                    logger.debug(f"Timeout verifying {url_norm}, skipping")
                    continue
                except Exception as e:
                    logger.debug(f"Failed to verify {url_norm}: {e}, skipping")
                    continue
        
        # Always ensure homepage is included if it was in the original list
        if base_url_norm in urls and base_url_norm not in verified:
            # Homepage should always be verified separately
            try:
                with httpx.Client(follow_redirects=True, timeout=5) as client:
                    r = client.get(base_url_norm, timeout=5)
                    if r.status_code == 200:
                        verified.insert(0, base_url_norm)
            except Exception:
                pass  # If homepage fails, that's a bigger problem
        
        logger.info(f"Verified {len(verified)} out of {len(urls)} URLs exist")
        return verified

    # -------------------------------------------------------------------------
    # Utility
    # -------------------------------------------------------------------------

    @staticmethod
    def _normalize_url(url: str) -> str:
        """Normalize URL by stripping whitespace and trailing slash."""
        if not url:
            return ""
        return url.strip().rstrip("/")
