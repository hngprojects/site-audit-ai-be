from fastapi import APIRouter, status
from app.platform.response import api_response


router = APIRouter()

@router.get("/health", tags=["health"])
async def health_check():
    return api_response(
        data={"status": "ok", "service": "Site Audit AI"},
        message="Service is healthy",
        status_code=status.HTTP_200_OK,
    )