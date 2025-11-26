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


# ─────────────────────────────────────────────────────────────
# Unified Ownership Functions (user_id priority, device_id fallback)
# ─────────────────────────────────────────────────────────────

async def create_site(
    db: AsyncSession,
    site_data: SiteCreate,
    user_id: str | None = None,
    device_id: str | None = None,
):
    """
    Create a site with flexible ownership.
    - If user_id is provided → site belongs to user (user_id takes priority)
    - Else if device_id is provided (from payload) → site belongs to device
    - At least one must be present (enforced by DB constraint)
    """
    normalized_url = normalize_url(site_data.root_url)
    if not is_valid_domain(normalized_url):
        raise ValueError("Invalid domain in root_url")

    # Extract device_id from payload if present (extra field)
    payload_device_id = getattr(site_data, "device_id", None)

    new_site = Site(
        user_id=user_id,
        device_id=device_id or payload_device_id,  # fallback to payload
        root_url=normalized_url,
        display_name=site_data.display_name,
        favicon_url=site_data.favicon_url,
        status=site_data.status or SiteStatus.active,
    )
    db.add(new_site)
    try:
        await db.commit()
        await db.refresh(new_site)
    except IntegrityError:
        await db.rollback()
        if user_id:
            raise ValueError("You already have a site with this root_url")
        else:
            raise ValueError("A site with this root_url already exists for this device")
    except Exception as e:
        await db.rollback()
        raise e
    return new_site


async def get_sites_for_owner(
    db: AsyncSession,
    user_id: str | None = None,
    device_id: str | None = None,
):
    """Get all non-deleted sites belonging to the current user or device"""
    query = select(Site).where(Site.status != SiteStatus.deleted)
    
    if user_id:
        query = query.where(Site.user_id == user_id)
    elif device_id:
        query = query.where(Site.device_id == device_id)
    else:
        # Should never happen due to route dependency
        raise HTTPException(status_code=400, detail="No ownership context provided")

    result = await db.execute(query)
    return result.scalars().all()


async def get_site_by_id_for_owner(
    db: AsyncSession,
    site_id: str,
    user_id: str | None = None,
    device_id: str | None = None,
):
    """Get a site by ID if it belongs to the current user or device"""
    query = select(Site).where(
        Site.id == site_id,
        Site.status != SiteStatus.deleted,
    )
    
    if user_id:
        query = query.where(Site.user_id == user_id)
    elif device_id:
        query = query.where(Site.device_id == device_id)
    else:
        raise HTTPException(status_code=400, detail="No ownership context provided")

    result = await db.execute(query)
    site = result.scalars().first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    return site


async def soft_delete_site_by_id_for_owner(
    db: AsyncSession,
    site_id: str,
    user_id: str | None = None,
    device_id: str | None = None,
):
    """Soft delete a site if it belongs to the current user or device"""
    stmt = (
        update(Site)
        .where(Site.id == site_id, Site.status != SiteStatus.deleted)
        .values(status=SiteStatus.deleted)
        .returning(Site)
    )
    
    if user_id:
        stmt = stmt.where(Site.user_id == user_id)
    elif device_id:
        stmt = stmt.where(Site.device_id == device_id)
    else:
        raise HTTPException(status_code=400, detail="No ownership context provided")

    result = await db.execute(stmt)
    site = result.scalars().first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    await db.commit()
    return site
