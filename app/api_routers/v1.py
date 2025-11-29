from fastapi import APIRouter

from app.features.auth.routes.auth import router as auth_router
from app.features.auth.routes.oauth import router as oauth_router
from app.features.auth.routes.users import router as users_router
from app.features.sites.routes.sites import router as sites_router
from app.features.scan.routes.scan import router as scan_router
from app.features.scan.routes.analysis import router as analysis_router
# from app.features.referral.routes.referral import router as referral_router
from app.features.referral.routes.referral_links import router as referral_links_router
from app.features.health.routes.health import router as health_router
from app.features.waitlist.routes.waitlist import router as waitlist_router


# Scan feature routes
from app.features.scan.routes.scan import router as scan_main_router
from app.features.scan.routes.discovery import router as scan_discovery_router
from app.features.scan.routes.selection import router as scan_selection_router
from app.features.scan.routes.scraping import router as scan_scraping_router
from app.features.scan.routes.analysis import router as scan_analysis_router
from app.features.scan.routes.pages import router as scan_pages_router
from app.features.request_form.routes.request_route import router as request_form_router

api_router = APIRouter()

from app.features.support.routes.email_support import router as support_router
from app.features.support.routes.contact_us import router as contact_router
from app.features.notifications.routes.notifications import router as notifications_router



# Register all feature routes
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(oauth_router)
api_router.include_router(sites_router)
api_router.include_router(scan_router)
api_router.include_router(analysis_router)
# api_router.include_router(referral_router)
api_router.include_router(referral_links_router)
api_router.include_router(health_router)
api_router.include_router(waitlist_router)
api_router.include_router(request_form_router)


# Register scan feature routes
api_router.include_router(scan_main_router)
api_router.include_router(scan_discovery_router)
api_router.include_router(scan_selection_router)
api_router.include_router(scan_scraping_router)
api_router.include_router(scan_analysis_router)
api_router.include_router(scan_pages_router)
api_router.include_router(contact_router)
api_router.include_router(notifications_router)
