from fastapi import APIRouter
from app.features.admin.routes.auth import router as auth_router
from app.features.admin.routes.dashboard import router as dashboard_router
from app.features.admin.routes.share_message import router as share_message_router


router = APIRouter(prefix="/admin", tags=["Admin"])

router.include_router(auth_router)
router.include_router(dashboard_router)
router.include_router(share_message_router)
