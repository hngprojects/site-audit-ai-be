from pydantic import BaseModel, field_validator


class CreateShareMessageRequest(BaseModel):
    platform: str
    message: str

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, v: str) -> str:
        return v.lower().strip()

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Message cannot be empty")
        return v.strip()


class UpdateShareMessageRequest(BaseModel):
    message: str

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Message cannot be empty")
        return v.strip()


class ShareMessageResponse(BaseModel):
    id: str
    platform: str
    message: str
    is_active: bool
