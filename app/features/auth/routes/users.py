from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.platform.db.session import get_db
from app.platform.response import api_response
from app.features.auth.models.user import User
from app.features.auth.schemas.auth import UserResponse, UpdateProfileRequest
from app.features.auth.routes.auth import get_current_user
from app.platform.utils.file_upload import save_profile_picture, delete_profile_picture


router = APIRouter(prefix="/users", tags=["User Management"])


@router.get(
    "/me",
    response_model=dict,
    summary="Get current user profile",
    description="Retrieve the profile information of the currently authenticated user"
)
async def get_my_profile(
    current_user: User = Depends(get_current_user)
):
    """Get the current user's profile."""
    return api_response(
        message="User profile retrieved successfully",
        data=UserResponse.model_validate(current_user).model_dump()
    )


@router.patch(
    "/me",
    response_model=dict,
    summary="Update current user profile",
    description="Update profile information (first_name, last_name, phone_number) for the current user"
)
async def update_my_profile(
    profile_data: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update the current user's profile information."""
    # Build update dict with only provided fields
    update_data = {}
    if profile_data.first_name is not None:
        update_data["first_name"] = profile_data.first_name
    if profile_data.last_name is not None:
        update_data["last_name"] = profile_data.last_name
    if profile_data.phone_number is not None:
        update_data["phone_number"] = profile_data.phone_number
    
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update"
        )
    
    # Update user in database
    stmt = (
        update(User)
        .where(User.id == current_user.id)
        .values(**update_data)
    )
    await db.execute(stmt)
    await db.commit()
    
    # Fetch fresh user object
    result = await db.execute(select(User).where(User.id == current_user.id))
    updated_user = result.scalar_one()
    
    return api_response(
        message="Profile updated successfully",
        data=UserResponse.model_validate(updated_user).model_dump()
    )


@router.post(
    "/me/profile-picture",
    response_model=dict,
    summary="Upload profile picture",
    description="Upload a new profile picture for the current user (max 3MB, jpg/png/webp/gif)"
)
async def upload_profile_picture(
    file: UploadFile = File(..., description="Profile picture image file"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload a new profile picture for the current user."""
    # Delete old profile picture if exists
    if current_user.profile_picture_url:
        delete_profile_picture(current_user.profile_picture_url)
    
    # Save new profile picture
    file_url = await save_profile_picture(file, str(current_user.id))
    
    # Update user in database
    stmt = (
        update(User)
        .where(User.id == current_user.id)
        .values(profile_picture_url=file_url)
    )
    await db.execute(stmt)
    await db.commit()
    
    # Fetch fresh user object
    result = await db.execute(select(User).where(User.id == current_user.id))
    updated_user = result.scalar_one()
    
    return api_response(
        message="Profile picture uploaded successfully",
        data={
            "profile_picture_url": file_url,
            "user": UserResponse.model_validate(updated_user).model_dump()
        }
    )


@router.delete(
    "/me/profile-picture",
    response_model=dict,
    summary="Delete profile picture",
    description="Delete the current user's profile picture"
)
async def delete_my_profile_picture(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete the current user's profile picture."""
    if not current_user.profile_picture_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No profile picture to delete"
        )
    
    # Delete file from disk
    delete_profile_picture(current_user.profile_picture_url)
    
    # Update user in database
    stmt = (
        update(User)
        .where(User.id == current_user.id)
        .values(profile_picture_url=None)
    )
    await db.execute(stmt)
    await db.commit()
    
    # Fetch fresh user object
    result = await db.execute(select(User).where(User.id == current_user.id))
    updated_user = result.scalar_one()
    
    return api_response(
        message="Profile picture deleted successfully",
        data=UserResponse.model_validate(updated_user).model_dump()
    )
