import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr
    username: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class UserCreate(UserBase):
    password: Optional[str] = None


class UserResponse(UserBase):
    id: uuid.UUID
    user_confirmed: bool
    date_created: datetime
    has_password: bool = Field(default=False)
    oauth_providers: list[str] = Field(default_factory=list)

    class Config:
        from_attributes = True
