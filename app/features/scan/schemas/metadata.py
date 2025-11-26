from typing import List, Optional
from pydantic import BaseModel, Field


class MetadataIssue(BaseModel):
    """Represents a validation issue with metadata"""
    field: str
    severity: str  # "error", "warning", "info"
    message: str


class TitleMetadata(BaseModel):
    """Structured title information with validation"""
    value: Optional[str] = None
    length: int = 0
    is_valid: bool = False
    issues: List[MetadataIssue] = Field(default_factory=list)


class DescriptionMetadata(BaseModel):
    """Structured description information with validation"""
    value: Optional[str] = None
    length: int = 0
    is_valid: bool = False
    issues: List[MetadataIssue] = Field(default_factory=list)


class OpenGraphMetadata(BaseModel):
    """Open Graph tags for social media sharing"""
    title: Optional[str] = None
    description: Optional[str] = None
    image: Optional[str] = None
    url: Optional[str] = None
    type: Optional[str] = None


class MetadataExtractionResult(BaseModel):
    """Complete metadata extraction result with validation"""
    url: str
    title: TitleMetadata
    description: DescriptionMetadata
    keywords: Optional[str] = None
    open_graph: Optional[OpenGraphMetadata] = None
    canonical_url: Optional[str] = None
    viewport: Optional[str] = None
    has_title: bool = False
    has_description: bool = False
    overall_valid: bool = False
    total_issues: int = 0

    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://example.com",
                "title": {
                    "value": "Example Site - Best Products",
                    "length": 30,
                    "is_valid": True,
                    "issues": []
                },
                "description": {
                    "value": "We sell the best products online with fast shipping and great prices.",
                    "length": 72,
                    "is_valid": False,
                    "issues": [
                        {
                            "field": "description",
                            "severity": "warning",
                            "message": "Description is too short. Recommended: 120-160 characters"
                        }
                    ]
                },
                "has_title": True,
                "has_description": True,
                "overall_valid": False,
                "total_issues": 1
            }
        }


class MetadataExtractionRequest(BaseModel):
    """Request schema for metadata extraction"""
    url: str = Field(..., description="The URL to extract metadata from")
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://example.com"
            }
        }