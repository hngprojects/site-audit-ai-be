# app/middlewares/rate_limit.py
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from redis.asyncio import Redis

from app.platform.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.redis = None
        self.memory_store = {}

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "testclient"

        # Skip limit if whitelisted
        if client_ip in settings.WHITELIST_IPS:
            return await call_next(request)

        path = request.url.path
        limit = settings.RATE_LIMITS.get(path)

        # If endpoint is not rate-limited, continue
        if limit is None:
            return await call_next(request)

        # ---------------------------
        # TEST MODE: In-memory store
        # ---------------------------
        if settings.FORCE_IN_MEMORY_RATE_LIMITER:
            key = f"{client_ip}:{path}"
            count, expiry = self.memory_store.get(key, (0, time.time() + 60))

            if time.time() > expiry:
                count = 0
                expiry = time.time() + 60

            if count >= limit:
                retry_after = int(expiry - time.time())
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too Many Requests - Rate limit exceeded."},
                    headers={"Retry-After": str(retry_after)},
                )

            self.memory_store[key] = (count + 1, expiry)
            return await call_next(request)

        # ---------------------------
        # PRODUCTION: Redis store
        # ---------------------------
        if self.redis is None:
            self.redis = await Redis.from_url(settings.REDIS_URL, decode_responses=True)

        key = f"rl:{client_ip}:{path}"
        current_count = await self.redis.get(key)

        if current_count is None:
            await self.redis.set(key, 1, ex=60)
        else:
            current_count = int(current_count)
            if current_count >= limit:
                ttl = await self.redis.ttl(key)
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too Many Requests - Rate limit exceeded."},
                    headers={"Retry-After": str(ttl)},
                )
            await self.redis.incr(key)

        return await call_next(request)

