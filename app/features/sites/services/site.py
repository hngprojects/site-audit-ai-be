import re

from fastapi import HTTPException, status
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.features.sites.models.site import Site, SiteStatus
from app.features.sites.schemas.site import SiteCreate


def normalize_url(url: str) -> str:
    url = url.strip()
    if url.startswith("//"):
        return "http:" + url
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", url):
        return "http://" + url
    return url


def is_valid_domain(url: str) -> bool:
    match = re.search(r"^[a-zA-Z][a-zA-Z0-9+.-]*://(?P<hostname>[^/:]+)", url)
    if not match:
        match = re.search(r"^(?P<hostname>[^/:]+)", url)
        if not match:
            return False
    hostname = match.group("hostname")
    return "." in hostname and not hostname.startswith(".") and not hostname.endswith(".")


async def create_site_for_user(db: AsyncSession, user_id: str, site_data: SiteCreate):
    normalized_url = normalize_url(site_data.root_url)
    if not is_valid_domain(normalized_url):
        raise ValueError("Invalid domain in root_url")
    new_site = Site(
        user_id=user_id,
        root_url=normalized_url,
        display_name=site_data.display_name,
        favicon_url=site_data.favicon_url,
        status=site_data.status,
    )
    db.add(new_site)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ValueError("Site with this root_url already exists for this user")
    except Exception as e:
        await db.rollback()
        raise e
    await db.refresh(new_site)
    return new_site


async def soft_delete_user_site_by_id(db: AsyncSession, user_id: str, site_id: str):
    stmt = (
        update(Site)
        .where(Site.id == site_id, Site.user_id == user_id)
        .values(status=SiteStatus.deleted)
        .returning(Site)
    )

    result = await db.execute(stmt)
    site = result.scalars().first()

    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")

    await db.commit()

    return site


async def get_site_by_id(db: AsyncSession, site_id: str, user_id: str):
    # Query the database for the site, ensuring it belongs to the user
    result = await db.execute(select(Site).where(Site.id == site_id, Site.user_id == user_id))
    site = result.scalars().first()
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found or does not belong to the user.",
        )
    return site


async def get_all_sites_for_user(db: AsyncSession, user_id: str):
    result = await db.execute(
        select(Site).where(Site.user_id == user_id, Site.status != SiteStatus.deleted)
    )
    return result.scalars().all()
