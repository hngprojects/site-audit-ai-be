import re
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.sites.models.site import Site
from app.features.sites.schemas.site import SiteCreate


def normalize_url(url: str) -> str:
    url = url.strip()
    if not re.match(r"^https?://", url):
        url = "https://" + url
    return url

def is_valid_domain(url: str) -> bool:
    domain = re.sub(r"^https?://", "", url)
    return "." in domain

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