"""
Issue Schemas

Response models for issue-related API endpoints.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime


class IssueSummary(BaseModel):
    """
    Summary of an issue for list views (e.g., in /results endpoint).
    
    Contains essential information for displaying issues in a list.
    """
    id: str
    title: str
    category: str  # seo, accessibility, performance, design
    severity: str  # critical, high, medium, low, info
    score_impact: Optional[float] = None
    page_url: str
    short_description: str
    affected_elements_count: int = 0
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "019ac123-4567-89ab-cdef-0123456789ab",
                "title": "Missing Page Title",
                "category": "seo",
                "severity": "critical",
                "score_impact": 12.0,
                "page_url": "https://example.com/about",
                "short_description": "This page has no <title> tag, which harms SEO and user experience.",
                "affected_elements_count": 1
            }
        }


class AffectedElement(BaseModel):
    """Details about an affected HTML element."""
    selector: Optional[str] = None
    html: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "selector": "head",
                "html": "<head>...</head>"
            }
        }


class Resource(BaseModel):
    """External resource/documentation link."""
    title: str
    url: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "HTML Title Element - MDN",
                "url": "https://developer.mozilla.org/en-US/docs/Web/HTML/Element/title"
            }
        }


class IssueDetail(BaseModel):
    """
    Detailed issue information for single issue view.
    
    Contains all available information about an issue including
    recommendations, affected elements, and helpful resources.
    """
    id: str
    title: str
    category: str
    severity: str
    description: str
    what_this_means: Optional[str] = None
    recommendation: Optional[str] = None
    score_impact: Optional[float] = None
    page_url: str
    page_id: str
    job_id: str
    business_impact: Optional[str] = None
    affected_elements_count: int = 0
    affected_elements: List[AffectedElement] = []
    resources: List[Resource] = []
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "019ac123-4567-89ab-cdef-0123456789ab",
                "title": "Missing Page Title",
                "category": "seo",
                "severity": "critical",
                "description": "The page does not have a <title> element in the <head> section...",
                "what_this_means": "Search engines use the title tag to understand page content...",
                "recommendation": "Add a descriptive <title> tag to the <head> section...",
                "score_impact": 12.0,
                "page_url": "https://example.com/about",
                "page_id": "019ac456-7890-abcd-ef01-234567890abc",
                "job_id": "019ac789-0abc-def0-1234-567890abcdef",
                "business_impact": "Missing titles reduce click-through rates from search results by up to 30%...",
                "affected_elements_count": 1,
                "affected_elements": [
                    {
                        "selector": "head",
                        "html": "<head>...</head>"
                    }
                ],
                "resources": [
                    {
                        "title": "HTML Title Element - MDN",
                        "url": "https://developer.mozilla.org/en-US/docs/Web/HTML/Element/title"
                    }
                ],
                "created_at": "2025-11-28T10:30:00Z"
            }
        }


class IssueListResponse(BaseModel):
    """Response wrapper for list of issues."""
    job_id: str
    total_issues: int
    issues: List[IssueSummary]
    
    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "019ac789-0abc-def0-1234-567890abcdef",
                "total_issues": 14,
                "issues": []
            }
        }
