from pydantic import BaseModel, Field
from typing import List, Optional


class Resource(BaseModel):
    title: str
    url: str


class Issue(BaseModel):
    title: str
    severity: str
    description: str = Field(..., description="Short, one-line sentence describing the issue")
    business_impact: str = Field(..., description="Short, one-line sentence explaining the impact")
    recommendation: str = Field(..., description="Short, one-line sentence with recommended action")
    resources: List[Resource] = Field(..., description="List of resources with short titles and URLs")


class IssueUnified(BaseModel):
    title: str
    category: str
    page_url: str
    severity: str
    description: str = Field(..., description="Short, one-line sentence describing the issue")
    business_impact: str = Field(..., description="Short, one-line sentence explaining the impact")
    recommendation: str = Field(..., description="Short, one-line sentence with recommended action")
    resources: List[Resource] = Field(..., description="List of resources with short titles and URLs")


class PageAnalysisResult(BaseModel):
    url: str
    scan_date: str

    usability_score: int
    usability_issues: List[Issue]

    performance_score: int
    performance_issues: List[Issue]

    seo_score: int
    seo_issues: List[Issue]
