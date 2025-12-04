from pydantic import BaseModel, EmailStr, Field

class LeadCreate(BaseModel):
    email: EmailStr = Field(..., description="Lead email")

class LeadOut(BaseModel):
    id: str
    email: EmailStr

    class Config:
        from_attributes = True
