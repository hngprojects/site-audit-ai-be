from pydantic import BaseModel, Field
from typing import List, Optional


class Resource(BaseModel):
    title: str
    url: str


class AffectedElement(BaseModel):
    selector: str
    html: str


class Issue(BaseModel):
    title: str
    severity: str
    description: str
    score_impact: int
    affected_element: AffectedElement
    business_impact: str
    recommendation: str
    resources: List[Resource]


class PageAnalysisResult(BaseModel):
    url: str
    scan_date: str

    usability_score: int
    usability_issues: List[Issue]

    performance_score: int
    performance_issues: List[Issue]

    seo_score: int
    seo_issues: List[Issue]
