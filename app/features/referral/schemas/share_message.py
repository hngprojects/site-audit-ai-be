from pydantic import BaseModel


class GetShareMessageResponse(BaseModel):
    message: str
    referralLink: str
