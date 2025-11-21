import random
import re
import string

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.auth.models.user import User


async def generate_unique_username(email: str, db: AsyncSession) -> str:
    """
    Generate a unique username from email

    Args:
        email: User's email address
        db: Database session

    Returns:
        A unique username
    """
    base_username = email.split("@")[0].lower()

    base_username = re.sub(r"[^a-z0-9_-]", "", base_username)

    if len(base_username) < 3:
        base_username = "user_" + base_username

    username = base_username

    result = await db.execute(select(User).where(User.username == username))

    while result.scalar_one_or_none():
        # Generate 4 random alphanumeric characters
        random_suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
        username = f"{base_username}_{random_suffix}"

        result = await db.execute(select(User).where(User.username == username))

    return username
