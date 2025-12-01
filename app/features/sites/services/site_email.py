from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.features.sites.models.site_email import SiteEmailAssociation
from app.features.sites.services.site import get_site_by_id_for_owner
from app.platform.services import email as email_service


async def associate_email_with_site(
    db: AsyncSession,
    *,
    site_id: str,
    email: str,
    user_id: str | None = None,
    device_id: str | None = None,
    send_notification: bool = True,
):
    site = await get_site_by_id_for_owner(db=db, site_id=site_id, user_id=user_id, device_id=device_id)

    stmt = select(SiteEmailAssociation).where(
        SiteEmailAssociation.site_id == str(site.id),
        SiteEmailAssociation.email == email,
    )
    result = await db.execute(stmt)
    existing = result.scalars().first()
    if existing:
        return existing, False

    association = SiteEmailAssociation(site_id=str(site.id), email=email)
    db.add(association)
    await db.commit()
    await db.refresh(association)

    if send_notification:
        subject = "You've been associated with a site on Site Audit AI"
        body = f"""
        <h3>Site Association Confirmed</h3>
        <p>The email <strong>{email}</strong> has been associated with the site (ID: {site.id}).</p>
        <p>If this wasn't you, please ignore this message.</p>
        """
        try:
            email_service.send_email(email, subject, body)
        except Exception:
            # Do not fail the operation if email sending fails
            pass

    return association, True
