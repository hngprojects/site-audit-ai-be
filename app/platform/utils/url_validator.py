from urllib.parse import urlparse, urlunparse
from typing import Tuple


def normalize_url(url: str) -> Tuple[str, bool]:

    url = url.strip()

    parsed = urlparse(url)

    if not parsed.scheme:
        normalized = f"https://{url}"
        return normalized, True
    
    return url, False


def validate_url(url: str) -> Tuple[bool, str, str]:
    if not url or not url.strip():
        return False, "", "URL cannot be empty"
    
    normalized_url, was_modified = normalize_url(url)
    
    try:
        parsed = urlparse(normalized_url)
        
        if not parsed.netloc:
            return False, normalized_url, "Invalid URL format: missing domain"
        
        if parsed.scheme not in ['http', 'https']:
            return False, normalized_url, f"Invalid URL scheme: {parsed.scheme} (must be http or https)"
        
        return True, normalized_url, ""
        
    except Exception as e:
        return False, normalized_url, f"URL parsing error: {str(e)}"