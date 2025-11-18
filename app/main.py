from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api_routers.v1 import api_router
from app.features.health.routes.health import router as health_router
from app.features.waitlist.routes.waitlist import router as waitlist_router

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(waitlist_router)
app.include_router(health_router)
app.include_router(api_router, prefix="/api/v1")

