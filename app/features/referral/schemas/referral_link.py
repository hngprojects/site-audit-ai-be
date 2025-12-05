from pydantic import BaseModel
from typing import Dict


class GenerateReferralLinkResponse(BaseModel):
    referralLink: str


class TrackClickRequest(BaseModel):
    source: str


class TrackClickResponse(BaseModel):
    status: str
    landingPageUrl: str


class ClicksBySourceResponse(BaseModel):
    totalClicks: int
    clicksBySource: Dict[str, int]
