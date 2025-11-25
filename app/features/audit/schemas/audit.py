from pydantic import BaseModel, EmailStr


class AuditIn(BaseModel):
    url: str


class UXOut(BaseModel):
    score: int
    issues: list[str]
    review: str


class SEOOut(BaseModel):
    score: int
    issues: list[str]
    summary: str


class SpeedOut(BaseModel):
    score: int
    warnings: list[str]
    summary: str


class AuditOut(BaseModel):
    ux: UXOut
    seo: SEOOut
    speed: SpeedOut
    overall_score: int
