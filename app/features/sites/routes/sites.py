from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.platform.db.session import get_db
from app.platform.response import api_response
from app.features.auth.routes.auth import get_current_user
from app.features.sites.schemas.site import SiteCreate, SiteResponse, SiteUpdate
from app.features.auth.models.user import User
from app.features.sites.services.site import create_site_for_user, soft_delete_user_site_by_id

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
    new_site = await create_site_for_user(db, user.id, request)
    return api_response(
        data=SiteResponse.from_orm(new_site),
        message="Site created successfully",
        status_code=status.HTTP_201_CREATED
    )


@router.patch(
    "/{site_id}/soft_delete",
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