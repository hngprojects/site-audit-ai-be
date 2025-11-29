import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api_routers.v1 import api_router
from app.features.health.routes.health import router as health_router
from app.features.waitlist.routes.waitlist import router as waitlist_router

# Configure logging to show INFO level messages
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

app = FastAPI(
    title="Site Audit AI API", description="API for website auditing and analysis", version="1.0.0"
)


# Root endpoint for basic info
@app.get("/", tags=["Info"])
def root():
    return {
        "app_name": "Site Audit AI API",
        "description": "AI-powered website health auditor for non-technical users.",
        "version": "1.0.0",
        "docs_url": "/docs",
        "api_base": "/api/v1",
    }


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create static directory if it doesn't exist
static_dir = Path("static")
static_dir.mkdir(exist_ok=True)

# Mount static files for serving uploaded images
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(waitlist_router)
app.include_router(health_router)
app.include_router(api_router, prefix="/api/v1")