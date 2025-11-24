from fastapi import APIRouter

from app.features.auth.routes.auth import router as auth_router
from app.features.auth.routes.oauth import router as oauth_router
from app.features.auth.routes.users import router as users_router
from app.features.sites.routes.sites import router as sites_router
from app.features.page_discovery.routes.discovery import router as discovery_router
from app.features.site_extraction.routes import extraction as extraction_routes

from app.features.support.routes.email_support import router as support_router

api_router = APIRouter()

# Register all feature routes
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(oauth_router)
api_router.include_router(support_router)
api_router.include_router(sites_router)
api_router.include_router(discovery_router)
api_router.include_router(extraction_routes.router)

