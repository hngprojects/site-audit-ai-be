from fastapi import APIRouter

from app.features.auth.routes.auth import router as auth_router
from app.features.auth.routes.oauth import router as oauth_router
from app.features.auth.routes.users import router as users_router
from app.features.sites.routes.sites import router as sites_router
from app.features.scan.routes.scan import router as scan_router
from app.features.scan.routes.analysis import router as analysis_router
from app.features.referral.routes.referral import router as referral_router
from app.features.health.routes.health import router as health_router
from app.features.waitlist.routes.waitlist import router as waitlist_router

api_router = APIRouter(prefix="/api/v1")

# Register all feature routes
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(oauth_router)
api_router.include_router(sites_router)
api_router.include_router(scan_router)
api_router.include_router(analysis_router)
api_router.include_router(referral_router)
api_router.include_router(health_router)
api_router.include_router(waitlist_router)
