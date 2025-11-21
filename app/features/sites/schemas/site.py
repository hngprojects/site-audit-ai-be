from pydantic import BaseModel, HttpUrl
from datetime import datetime
from typing import Optional

class SiteBase(BaseModel):
    url: HttpUrl
    name: Optional[str] = None

class SiteCreate(SiteBase):
    pass

class SiteResponse(SiteBase):
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
