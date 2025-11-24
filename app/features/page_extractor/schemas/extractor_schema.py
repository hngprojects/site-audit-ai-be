from typing import List
from pydantic import BaseModel, HttpUrl

class ExtractorRequest(BaseModel):
    url: HttpUrl

