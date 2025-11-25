from uuid import UUID

from pydantic import BaseModel, EmailStr

from app.platform.schemas import APIResponse


class WaitlistIn(BaseModel):
    full_name: str
    email: EmailStr
    what_best_describes_you: str | None = None


class WaitlistOut(BaseModel):
    id: UUID
    full_name: str
    email: EmailStr

    class Config:
        from_attributes = True


class WaitListResponse(APIResponse[WaitlistOut]):
    pass


# Standardized API Response Schema
class WaitlistResponse(BaseModel):
    status_code: int
    success: bool
    message: str
    data: WaitlistOut
