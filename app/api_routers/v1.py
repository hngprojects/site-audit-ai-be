from fastapi import APIRouter
from app.features.auth.routes.verify_email import router as verify_email_router

api_router = APIRouter()

#routes
api_router.include_router(verify_email_router)