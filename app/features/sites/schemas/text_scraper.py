from pydantic import BaseModel, HttpUrl
from typing import List, Optional, Dict, Any

class TextScraperRequest(BaseModel):
    url: HttpUrl
    keywords: Optional[List[str]] = []

# Simpler response model matching the direct output
class TextScraperResponse(BaseModel):
    word_count: Optional[int] = None
    header_body_ratio: Optional[float] = None
    readability_score: Optional[float] = None
    keyword_analysis: Optional[Dict[str, Any]] = None
    error: Optional[str] = None # Added incase of error