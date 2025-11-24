from typing import List
from pydantic import BaseModel, HttpUrl

class DiscoveryRequest(BaseModel):
    url: HttpUrl
    top_n: int = 20

class DiscoveryResponse(BaseModel):
    subdomains: List[str]
    pages: List[str]
    important_pages: List[str]