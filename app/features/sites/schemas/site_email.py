from pydantic import BaseModel, EmailStr


class SiteEmailAssociateRequest(BaseModel):
    email: EmailStr


class SiteEmailAssociationResponse(BaseModel):
    id: str
    site_id: str
    email: EmailStr

    class Config:
        from_attributes = True
