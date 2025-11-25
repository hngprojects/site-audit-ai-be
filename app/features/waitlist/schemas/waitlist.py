from uuid import UUID

from pydantic import BaseModel, EmailStr


class WaitlistIn(BaseModel):
    name: str
    email: EmailStr


class WaitlistOut(BaseModel):
    id: UUID
    name: str
    email: EmailStr

    class Config:
        from_attributes = True


# Standardized API Response Schema
class WaitlistResponse(BaseModel):
    status_code: int
    success: bool
    message: str
    data: WaitlistOut
