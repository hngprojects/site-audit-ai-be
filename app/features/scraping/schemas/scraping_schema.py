from pydantic import BaseModel, HttpUrl

class ScrapeRequest(BaseModel):
    url: HttpUrl

class ScrapeResponse(BaseModel):
    url: str
    title: str
    content_preview: str
