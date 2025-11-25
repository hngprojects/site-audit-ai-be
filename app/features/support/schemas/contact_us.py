from pydantic import BaseModel, EmailStr

from app.platform.schemas import APIResponse


class ContactUsIn(BaseModel):
    full_name: str
    phone_number: str
    email: EmailStr
    message: str


class ContactUsOut(BaseModel):
    ticket_id: str


class ContactUsResponse(APIResponse[ContactUsOut]):
    pass
