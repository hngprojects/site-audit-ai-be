from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.sites.models.site import Site
from app.features.sites.schemas.site import SiteCreate
from sqlalchemy.future import select


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

async def get_site_by_id(db: AsyncSession, site_id: str, user_id: str):
    # Query the database for the site, ensuring it belongs to the user
    result = await db.execute(
        select(Site).where(Site.id == site_id, Site.user_id == user_id)
    )
    site = result.scalars().first()
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found or does not belong to the user."
        )
    return site
