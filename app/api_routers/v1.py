from fastapi import APIRouter

from app.features.auth.routes.auth import router as auth_router
from app.features.auth.routes.oauth import router as oauth_router
from app.features.waitlist.routes.waitlist import router as waitlist_router
from app.features.health.routes.health import router as health_router


api_router = APIRouter()

# Register all feature routes
api_router.include_router(auth_router)
api_router.include_router(oauth_router)
api_router.include_router(waitlist_router)

