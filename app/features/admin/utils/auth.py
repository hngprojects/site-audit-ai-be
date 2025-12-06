from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.admin.services.auth import AdminAuthService
from app.features.auth.utils.security import decode_access_token
from app.platform.db.session import get_db

security = HTTPBearer()


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(credentials.credentials)
        admin_id: str | None = payload.get("sub")
        email: str | None = payload.get("email")
        is_admin: bool = payload.get("is_admin", False)

        if admin_id is None or email is None or not is_admin:
            raise credentials_exception

        auth_service = AdminAuthService(db)
        admin = await auth_service.get_admin_by_id(admin_id)

        if admin is None:
            raise credentials_exception

        if not bool(admin.is_active):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Admin account is inactive"
            )

        return {
            "id": str(admin.id),
            "email": admin.email,
            "is_super_admin": admin.is_super_admin,
            "is_active": admin.is_active,
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_super_admin(current_admin: dict = Depends(get_current_admin)) -> dict:
    if not current_admin.get("is_super_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Super admin access required"
        )
    return current_admin
