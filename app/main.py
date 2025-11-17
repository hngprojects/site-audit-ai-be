from fastapi import FastAPI
from app.features.health.endpoints import router as health_router

app = FastAPI()


app.include_router(health_router, prefix="")