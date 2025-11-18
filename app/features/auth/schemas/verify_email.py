from pydantic import BaseModel, EmailStr, StringConstraints as constr
from typing import Annotated

class VerifyOTPRequest(BaseModel):
    email: EmailStr
    code: Annotated[str, constr(min_length=6, max_length=6)]

class VerifyOTPResponse(BaseModel):
    success: bool
    temp_token: str | None = None
    message: str