from fastapi import FastAPI
from app.middlewares.rate_limit import RateLimitMiddleware
from app.features.health.endpoints import router as health_router
from app.features.waitlist.endpoints import router as waitlist_router

app = FastAPI()

# Register rate limit middleware
app.add_middleware(RateLimitMiddleware)

app.include_router(health_router)
app.include_router(waitlist_router)

