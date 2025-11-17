import time
from app.platform.config import settings
from redis.asyncio import Redis
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from fastapi import Request


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.redis = None

    async def dispatch(self, request: Request, call_next):
        # 1. Get client IP
        client_ip = request.client.host if request.client else "testclient"

        # 2. Whitelist check
        if client_ip in settings.WHITELIST_IPS:
            return await call_next(request)

        # 3. Redis connection (lazy init)
        if self.redis is None:
            self.redis = await Redis.from_url(settings.REDIS_URL, decode_responses=True)

        # 4. Determine which endpoint limit applies
        path = request.url.path

        if path == "/waitlist":
            limit = settings.RATE_LIMITS["waitlist"]
        elif path == "/waitlist/stats":
            limit = settings.RATE_LIMITS["stats"]
        else:
            return await call_next(request)  # no limits for others

        # 5. Prepare counter key
        key = f"rl:{client_ip}:{path}"
        current_count = await self.redis.get(key)

        if current_count is None:
            # New counter
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

        # 6. Continue request
        return await call_next(request)
