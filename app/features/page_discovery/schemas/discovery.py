from typing import List, Optional
from pydantic import BaseModel, HttpUrl

class DiscoveryRequest(BaseModel):
    url: HttpUrl
    top_n: int = 20

class DiscoveryResponse(BaseModel):
    subdomains: Optional[List[str]] = None  # subdomain scanning is disabled for MVP
    pages: List[str]
    important_pages: List[str]