from datetime import datetime
from typing import List
from pydantic import BaseModel, Field, ConfigDict, HttpUrl

from app.features.request_form.models.request_form import RequestStatus


class RequestFormCreate(BaseModel):
    user_id: str = Field(..., description="User ID (required)")
    job_id: str = Field(..., description="Job ID (required)")
    website: HttpUrl | str = Field(..., description="Target website URL (required)")
    selected_category: List[str] = Field(..., min_length=1, description="At least one category must be selected")


class RequestFormResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    request_id: str
    user_id: str
    job_id: str
    selected_category: list[str]
    status: RequestStatus
    created_at: datetime


class RequestFormStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    request_id: str
    status: RequestStatus
    updated_at: datetime
