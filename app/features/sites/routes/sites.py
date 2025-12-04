from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.sites.schemas.site import SiteCreate, SiteResponse, SitePeriodicScanUpdate
from app.features.sites.services.site import (
    create_site,
    get_sites_for_owner,
    get_site_by_id_for_owner,
    soft_delete_site_by_id_for_owner,
    update_site_scan_frequency,
)
from app.features.sites.dependencies.site import get_owner_context
from app.platform.db.session import get_db
from app.platform.response import api_response

router = APIRouter(prefix="/sites", tags=["Sites"])


@router.post(
    "",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new site",
    description="Create a site for the authenticated user or anonymous device",
)
async def create_site_route(
    request: SiteCreate,
    owner: dict = Depends(get_owner_context),
    db: AsyncSession = Depends(get_db),
):
    user_id = owner["user_id"]
    device_id = getattr(request, "device_id", None)

    if not user_id and not device_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authentication or 'device_id' in payload is required",
        )

    new_site = await create_site(
        db=db,
        site_data=request,
        user_id=user_id,
        device_id=device_id,
    )

    return api_response(
        data=SiteResponse.from_orm(new_site),
        message="Site created successfully",
        status_code=status.HTTP_201_CREATED,
    )


@router.get(
    "/{site_id}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Get site details",
    description="Retrieve a specific site belonging to the current user or device",
)
async def get_site(
    site_id: str,
    owner: dict = Depends(get_owner_context),
    db: AsyncSession = Depends(get_db),
):
    user_id = owner["user_id"]
    device_id = getattr(request, "device_id", None) if not user_id else None

    site = await get_site_by_id_for_owner(
        db=db,
        site_id=site_id,
        user_id=user_id,
        device_id=device_id,
    )

    return api_response(
        data=SiteResponse.from_orm(site),
        message="Site retrieved successfully",
        status_code=status.HTTP_200_OK,
    )


@router.patch(
    "/{site_id}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Soft delete an existing site",
    description="Soft delete a site belonging to the current user or device",
)
async def soft_delete_site(
    site_id: str,
    owner: dict = Depends(get_owner_context),
    db: AsyncSession = Depends(get_db),
):
    user_id = owner["user_id"]
    device_id = getattr(request, "device_id", None) if not user_id else None

    updated_site = await soft_delete_site_by_id_for_owner(
        db=db,
        site_id=site_id,
        user_id=user_id,
        device_id=device_id,
    )

    return api_response(
        data=SiteResponse.from_orm(updated_site),
        message="Site soft deleted successfully",
        status_code=status.HTTP_200_OK,
    )


@router.get(
    "",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Get all sites",
    description="Retrieve all non-deleted sites belonging to the current user or device",
)
async def get_all_sites(
    owner: dict = Depends(get_owner_context),
    db: AsyncSession = Depends(get_db),
):
    user_id = owner["user_id"]
    device_id = getattr(request, "device_id", None) if not user_id else None

    if not user_id and not device_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authentication or 'device_id' in payload is required",
        )

    sites = await get_sites_for_owner(
        db=db,
        user_id=user_id,
        device_id=device_id,
    )

    return api_response(
        data=[SiteResponse.from_orm(site) for site in sites],
        message="Sites retrieved successfully",
        status_code=status.HTTP_200_OK,
    )


@router.patch(
    "/{site_id}/scan-frequency",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Update periodic scan frequency",
    description="""
    Configure periodic scanning settings for a site.    
    
    Scan Frequency Options:
    - daily: Scan once every 24 hours
    - weekly: Scan once every 7 days
    - monthly: Scan once every 30 days
    - disabled: Disable periodic scanning 
    
    Parameters:
    - scan_frequency: One of the frequency options above
    - scan_frequency_enabled: Boolean to enable/disable scanning (quick toggle)
    
    Note: When enabled, the first scan will be scheduled based on the selected frequency.
    Email notifications will be sent to the user after each scan completes.
    """,
)
async def update_scan_frequency(
    site_id: str,
    request: SitePeriodicScanUpdate,
    owner: dict = Depends(get_owner_context),
    db: AsyncSession = Depends(get_db),
):
    user_id = owner["user_id"]
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required for periodic scanning",
        )

    updated_site = await update_site_scan_frequency(
        db=db,
        site_id=site_id,
        scan_frequency=request.scan_frequency,
        scan_frequency_enabled=request.scan_frequency_enabled,
        user_id=user_id,
    )

    return api_response(
        data=SiteResponse.from_orm(updated_site),
        message="Scan frequency updated successfully",
        status_code=status.HTTP_200_OK,
    )