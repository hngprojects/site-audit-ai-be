from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.platform.db.session import get_db
from app.platform.response import api_response
from app.features.auth.routes.auth import get_current_user
from app.features.sites.schemas.site import SiteCreate, SiteResponse
from app.features.auth.models.user import User
from app.features.sites.services.site import create_site_for_user, get_site_by_id, soft_delete_user_site_by_id, get_all_sites_for_user


router = APIRouter(prefix="/sites", tags=["Sites"])

@router.post(
    "",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new site",
    description="Add a new site for the authenticated user"
)
async def create_site(
    request: SiteCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    try:
        new_site = await create_site_for_user(db, user.id, request)
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(ve)
        )
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Site with this root_url already exists for this user"
        )
    return api_response(
        data=SiteResponse.from_orm(new_site),
        message="Site created successfully",
        status_code=status.HTTP_201_CREATED
    )


@router.get(
    "/{site_id}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Get site details",
    description="Retrieve a specific site belonging to the authenticated user"

)
async def get_site(
    site_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    site = await get_site_by_id(db, site_id, user.id)
    return api_response(
        data=SiteResponse.from_orm(site),
        message="Site retrieved successfully",
        status_code=status.HTTP_200_OK
    )


@router.patch(
    "/{site_id}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Soft deletes an existing site",
    description="Soft deletes a site's details for the authenticated user in order to preserve history",
)
async def soft_delete_site(
    site_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    updated_site = await soft_delete_user_site_by_id(
        db=db,
        user_id=user.id,
        site_id=site_id,
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
    summary="Get all sites for the authenticated user",
    description="Retrieve all non-deleted sites belonging to the authenticated user"
)
async def get_all_sites(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    sites = await get_all_sites_for_user(db, user.id)
    return api_response(
        data=[SiteResponse.from_orm(site) for site in sites],
        message="Sites retrieved successfully",
        status_code=status.HTTP_200_OK
    )