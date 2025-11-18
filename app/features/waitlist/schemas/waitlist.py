from pydantic import BaseModel, EmailStr 
from datetime import datetime

class WaitlistIn(BaseModel):
    name: str
    email: EmailStr

class WaitlistOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    created_at: datetime

    class Config:
        from_attributes = True


# Standardized API Response Schema
class WaitlistResponse(BaseModel):
    status_code: int
    success: bool
    message: str
    data: WaitlistOut