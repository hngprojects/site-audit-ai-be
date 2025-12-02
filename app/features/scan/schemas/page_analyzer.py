from pydantic import BaseModel, Field
from typing import List, Optional

class Issue(BaseModel):
    title: str
    severity: str
    description: str
    score_impact: int
    business_impact: str
    recommendation: str


class PageAnalysisResult(BaseModel):
    url: str
    scan_date: str

    usability_score: int
    usability_issues: List[Issue]

    performance_score: int
    performance_issues: List[Issue]

    seo_score: int
    seo_issues: List[Issue]
