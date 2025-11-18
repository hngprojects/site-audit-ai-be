from pydantic import BaseModel, EmailStr


class WaitlistIn(BaseModel):
    name: str
    email: EmailStr
    referred_by: str | None = None


class WaitlistOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    referral_code: str
    referred_by: str | None = None
    referral_count: int

    class Config:
        from_attributes = True
