from typing import List
from pydantic import BaseModel, HttpUrl

class ExtractorRequest(BaseModel):
    url: HttpUrl

class ExtractorResponse(BaseModel):
    subdomains: List[str]
    pages: List[str]
    important_pages: List[str]