from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.platform.db.session import get_db
from app.features.auth.routes.auth import get_current_user
from app.features.auth.models.user import User
from app.features.sites.services import site_service

router = APIRouter(prefix="/sites", tags=["Sites"])

@router.delete("/{site_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_site(
    site_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a single site.
    Only the owner of the site can delete it.
    """
    await site_service.delete_site(db, site_id, current_user.id)
    return None
