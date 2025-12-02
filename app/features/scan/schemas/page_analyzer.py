from pydantic import BaseModel, Field
from typing import List, Optional


class Resource(BaseModel):
    title: str
    url: str


class AffectedElement(BaseModel):
    selector: str = None
    html: str = None


class Issue(BaseModel):
    title: str
    severity: str
    description: str = Field(...,
                             description="Short, one-line sentence describing the issue")
    score_impact: int = Field(
        ..., description="Positive Integer between 0-100 quantifying how this issue affects the total score")
    affected_element: AffectedElement
    business_impact: str = Field(...,
                                 description="Short, one-line sentence explaining the impact")
    recommendation: str = Field(...,
                                description="Short, one-line sentence with recommended action")
    resources: List[Resource] = Field(
        ..., description="List of resources with short titles and URLs")


class IssueUnified(BaseModel):
    title: str
    category: str
    page_url: str
    severity: str
    description: str = Field(...,
                             description="Short, one-line sentence describing the issue")
    score_impact: int = Field(
        ..., description="Positive Integer between 0-100 quantifying how this issue affects the total score")
    affected_element: AffectedElement
    business_impact: str = Field(...,
                                 description="Short, one-line sentence explaining the impact")
    recommendation: str = Field(...,
                                description="Short, one-line sentence with recommended action")
    resources: List[Resource] = Field(
        ..., description="List of resources with short titles and URLs")


class PageAnalysisResult(BaseModel):
    url: str
    scan_date: str

    usability_score: int
    usability_issues: List[Issue]

    performance_score: int
    performance_issues: List[Issue]

    seo_score: int
    seo_issues: List[Issue]
