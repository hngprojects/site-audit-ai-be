from fastapi import APIRouter
from app.features.auth.routes.auth import router as auth_router


api_router = APIRouter()

# Register all feature routes
api_router.include_router(auth_router)

