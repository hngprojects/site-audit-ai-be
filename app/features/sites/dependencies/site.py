from typing import Optional, Dict
from fastapi import Depends
from app.features.auth.models.user import User
from app.features.auth.routes.auth import get_current_user  # ← Yes, the real one (not optional!)


async def get_owner_context(
    current_user: Optional[User] = Depends(get_current_user),
) -> Dict[str, Optional[str]]:
    """
    Dependency that determines ownership context for the current request.

    Returns:
        {"user_id": "abc123" | None}

    - If user is authenticated → returns {"user_id": "<user_id>"}
    - If user is NOT authenticated → returns {"user_id": None}
      (device_id will be read from the request payload in the route)

    This design allows:
    - Preserving device_id in DB even for logged-in users (for history/claiming)
    - Clean priority: user_id always wins for ownership queries
    """
    if current_user:
        return {"user_id": current_user.id}
    return {"user_id": None}