from pydantic import BaseModel, EmailStr

class WaitlistIn(BaseModel):
    name: str
    email: EmailStr

class WaitlistOut(BaseModel):
    id: int
    name: str
    email: EmailStr

    class Config:
        orm_mode = True