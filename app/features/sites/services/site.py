from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from fastapi import HTTPException, status
from app.features.sites.models.site import Site
from app.features.sites.schemas.site import SiteCreate, SiteUpdate

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

async def update_site_for_user(db: AsyncSession, user_id: str, site_id: str, site_data: SiteUpdate):
    # Check if site exists and belongs to user
    result = await db.execute(
        select(Site).where(Site.id == site_id, Site.user_id == user_id)
    )
    site = result.scalar_one_or_none()
    
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found or access denied"
        )
    
    # Build update dict with only provided fields
    update_data = {}
    if site_data.display_name is not None:
        update_data["display_name"] = site_data.display_name
    if site_data.favicon_url is not None:
        update_data["favicon_url"] = str(site_data.favicon_url)
    if site_data.status is not None:
        update_data["status"] = site_data.status
    
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update"
        )
    
    # Update site in database
    stmt = (
        update(Site)
        .where(Site.id == site_id)
        .values(**update_data)
    )
    await db.execute(stmt)
    await db.commit()
    
    # Fetch updated site
    result = await db.execute(select(Site).where(Site.id == site_id))
    updated_site = result.scalar_one()
    
    return updated_site