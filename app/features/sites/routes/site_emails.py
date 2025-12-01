from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.sites.dependencies.site import get_owner_context
from app.features.sites.schemas.site_email import (
    SiteEmailAssociateRequest,
    SiteEmailAssociationResponse,
)
from app.features.sites.services.site_email import associate_email_with_site
from app.platform.utils.rate_limit import rate_limit
from app.platform.db.session import get_db
from app.platform.response import api_response

router = APIRouter(prefix="/sites", tags=["Sites"])


@router.post(
    "/{site_id}/emails",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Associate an email with a site",
    description="Associates an email address with the specified site and sends a notification email.",
)
async def associate_email(
    site_id: str,
    request: SiteEmailAssociateRequest,
    owner: dict = Depends(get_owner_context),
    db: AsyncSession = Depends(get_db),
    raw_request: Request = None,
):
    user_id = owner.get("user_id")
    device_id = None if user_id else None

    try:
        # Rate limit key: prefer user_id, else IP address
        client_ip = raw_request.client.host if raw_request and raw_request.client else "unknown"
        key = f"site-email:{user_id or client_ip}:{site_id}"
        rate_limit(key)
        association, created = await associate_email_with_site(
            db,
            site_id=site_id,
            email=request.email,
            user_id=user_id,
            device_id=device_id,
            send_notification=True,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    message = "Email association created successfully" if created else "Email already associated"
    status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK

    return api_response(
        data=SiteEmailAssociationResponse.model_validate(association).model_dump(),
        message=message,
        status_code=status_code,
    )
