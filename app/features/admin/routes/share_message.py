from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.admin.schemas.share_message import (
    CreateShareMessageRequest,
    ShareMessageResponse,
    UpdateShareMessageRequest,
)
from app.features.admin.services.share_message import AdminShareMessageService
from app.platform.db.session import get_db
from app.platform.response import api_response

router = APIRouter(prefix="/share-messages", tags=["Admin - Share Messages"])


@router.post(
    "",
    response_model=ShareMessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new share message template",
)
async def create_share_message(
    request_body: CreateShareMessageRequest, db: AsyncSession = Depends(get_db)
):
    """
    Create a new share message template for a platform.

    Supported placeholders:
    - {referral_link}
    - {first_name}
    - {last_name}
    - {email}
    - {username} (falls back to first_name if not available)
    - {site_name}
    """
    service = AdminShareMessageService(db)
    template = await service.create_template(
        platform=request_body.platform, message=request_body.message
    )

    return api_response(
        data={
            "id": str(template.id),
            "platform": template.platform,
            "message": template.message,
            "is_active": template.is_active,
        },
        message="Share message template created successfully",
        status_code=status.HTTP_201_CREATED,
    )


@router.put(
    "/{platform}",
    response_model=ShareMessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a share message template",
)
async def update_share_message(
    platform: str, request_body: UpdateShareMessageRequest, db: AsyncSession = Depends(get_db)
):
    """
    Update an existing share message template.
    """
    service = AdminShareMessageService(db)
    template = await service.update_template(
        platform=platform.lower(), message=request_body.message
    )

    return api_response(
        data={
            "id": str(template.id),
            "platform": template.platform,
            "message": template.message,
            "is_active": template.is_active,
        },
        message="Share message template updated successfully",
        status_code=status.HTTP_200_OK,
    )


@router.get(
    "",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="List all share message templates",
)
async def list_share_messages(db: AsyncSession = Depends(get_db)):
    """
    List all share message templates.
    """
    service = AdminShareMessageService(db)
    templates = await service.list_templates()

    data = [
        {
            "id": str(template.id),
            "platform": template.platform,
            "message": template.message,
            "is_active": template.is_active,
        }
        for template in templates
    ]

    return api_response(
        data={"templates": data},
        message="Share message templates retrieved successfully",
        status_code=status.HTTP_200_OK,
    )


@router.get(
    "/{platform}",
    response_model=ShareMessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a specific share message template",
)
async def get_share_message(platform: str, db: AsyncSession = Depends(get_db)):
    """
    Get a specific share message template by platform.
    """
    service = AdminShareMessageService(db)
    template = await service.get_template(platform.lower())

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template for platform '{platform}' not found",
        )

    return api_response(
        data={
            "id": str(template.id),
            "platform": template.platform,
            "message": template.message,
            "is_active": template.is_active,
        },
        message="Share message template retrieved successfully",
        status_code=status.HTTP_200_OK,
    )


@router.delete(
    "/{platform}",
    response_model=ShareMessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete a share message template",
)
async def delete_share_message(platform: str, db: AsyncSession = Depends(get_db)):
    """
    Delete a share message template.
    """
    service = AdminShareMessageService(db)
    await service.delete_template(platform.lower())

    return api_response(
        data={"platform": platform.lower()},
        message="Share message template deleted successfully",
        status_code=status.HTTP_200_OK,
    )
