from fastapi import FastAPI
from app.features.health.endpoints import router as health_router
from app.features.waitlist.endpoints import router as waitlist_router
from app.features.auth.endpoints import router as auth_router

app = FastAPI()

app.include_router(health_router)
app.include_router(waitlist_router)
app.include_router(auth_router)