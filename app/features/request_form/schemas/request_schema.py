from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

from app.features.request_form.models.request_form import RequestStatus


class RequestFormCreate(BaseModel):
    user_id: str = Field(..., description="User ID (required)")
    job_id: str = Field(..., description="Job ID (required)")
    issues: List[str] = Field(..., min_length=1, description="At least one issue must be selected")
    additional_notes: Optional[str] = Field(None, description="Optional additional notes")


class RequestFormUpdate(BaseModel):
    issues: Optional[List[str]] = Field(None, description="Updated issues (cannot be empty if provided)")
    additional_notes: Optional[str] = Field(None, description="Updated additional notes")

class RequestFormStatusUpdate(BaseModel):
    status: RequestStatus = Field(..., description="New status value")

class RequestFormResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    request_id: str
    user_id: str
    job_id: str
    issues: list[str]
    additional_notes: Optional[str]
    status: RequestStatus
    created_at: datetime

class RequestFormStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    request_id: str
    status: RequestStatus
    updated_at: datetime
