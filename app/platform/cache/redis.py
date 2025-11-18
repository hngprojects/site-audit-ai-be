import os
from redis.asyncio import Redis

# Get the Redis URL from environment variable
REDIS_URL = os.getenv("REDIS_URL")

# Create a Redis client
redis = Redis.from_url(
    REDIS_URL,
    encoding="utf-8",
    decode_responses=True
)
