from sqlalchemy.ext.asyncio import AsyncSession
from app.features.sites.models.site import Site
from app.features.sites.schemas.site import SiteCreate, SiteUpdate
from sqlalchemy import select, update
from fastapi import HTTPException


async def create_site_for_user(db: AsyncSession, user_id: str, site_data: SiteCreate):
    new_site = Site(
        user_id=user_id,
        root_url=str(site_data.root_url),
        display_name=site_data.display_name,
        favicon_url=str(site_data.favicon_url) if site_data.favicon_url else None,
        status=site_data.status,
    )
    db.add(new_site)
    await db.commit()
    await db.refresh(new_site)
    return new_site


async def update_user_site_by_id(db: AsyncSession,
    user_id: str,
    site_id: str,
    site_data: SiteUpdate):
    
     # Make sure the site exists and belongs to this user
    result = await db.execute(
        select(Site).where(
            Site.id == site_id,
            Site.user_id == user_id,
        )
    )
    site = result.scalars().first()

    if not site:
        # Either doesn't exist or doesn't belong to this user
        raise HTTPException(status_code=404, detail="Site not found")
    
    # Only update fields that were actually sent in the request
    if site_data.display_name is not None:
        site.display_name = site_data.display_name

    if site_data.favicon_url is not None:
        site.favicon_url = str(site_data.favicon_url)

    if site_data.status is not None:
        site.status = site_data.status

    await db.commit()
    await db.refresh(site)

    return site