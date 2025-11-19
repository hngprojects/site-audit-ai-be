from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.middlewares.rate_limit import RateLimitMiddleware
from app.api_routers.v1 import api_router
from app.features.waitlist.routes.waitlist import router as waitlist_router
from app.features.health.routes.health import router as health_router
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = FastAPI(
    title="Site Audit AI API",
    description="API for website auditing and analysis",
    version="1.0.0"
)

# Middlewares
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(waitlist_router)
app.include_router(health_router)
app.include_router(api_router, prefix="/api/v1")
