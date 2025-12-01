from fastapi import APIRouter
from app.features.admin.routes.share_message import router as share_message_router


router = APIRouter(prefix="/admin", tags=["Admin"])


router.include_router(share_message_router)
