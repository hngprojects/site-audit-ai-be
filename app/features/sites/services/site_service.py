from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from app.features.sites.models.site import Site

async def delete_site(db: AsyncSession, site_id: str, user_id: str):
    """
    Delete a site by ID.
    Ensures the site belongs to the user before deleting.
    """
    result = await db.execute(select(Site).where(Site.id == site_id))
    site = result.scalar_one_or_none()

    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found"
        )

    if site.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this site"
        )

    # TODO: Trigger background task to cleanup scan results (Celery)
    # cleanup_scan_results.delay(site_id)

    await db.delete(site)
    await db.commit()
    return True
