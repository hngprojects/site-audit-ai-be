from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.admin.schemas.auth import (
    AdminAuthResponse,
    AdminLoginRequest,
    AdminPasswordChangeRequest,
    AdminRegistrationRequest,
)
from app.features.admin.services.auth import AdminAuthService
from app.features.admin.utils.auth import get_current_admin, get_super_admin
from app.platform.db.session import get_db
from app.platform.response import api_response

router = APIRouter(prefix="/auth", tags=["Admin - Authentication"])


@router.post(
    "/register",
    response_model=AdminAuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new admin (super admin only)",
)
async def register_admin(
    admin_data: AdminRegistrationRequest,
    current_admin: dict = Depends(get_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new admin account. Only super admins can create new admins.
    """
    auth_service = AdminAuthService(db)

    admin = await auth_service.create_admin(admin_data=admin_data, created_by=current_admin["id"])

    access_token_expires = None
    access_token = auth_service.create_access_token(
        data={"sub": str(admin.id), "email": admin.email, "is_admin": True},
        expires_delta=access_token_expires,
    )

    return api_response(
        data={
            "admin": auth_service.admin_to_response(admin),
            "access_token": access_token,
            "token_type": "bearer",
        },
        message="Admin registered successfully",
        status_code=status.HTTP_201_CREATED,
    )


@router.post(
    "/login",
    response_model=AdminAuthResponse,
    status_code=status.HTTP_200_OK,
    summary="Login as admin",
)
async def login_admin(login_data: AdminLoginRequest, db: AsyncSession = Depends(get_db)):
    """
    Authenticate an admin and return access token.
    """
    auth_service = AdminAuthService(db)

    admin, access_token = await auth_service.login_admin(login_data)

    return api_response(
        data={
            "admin": auth_service.admin_to_response(admin),
            "access_token": access_token,
            "token_type": "bearer",
        },
        message="Admin login successful",
        status_code=status.HTTP_200_OK,
    )


@router.get(
    "/me",
    status_code=status.HTTP_200_OK,
    summary="Get current admin profile",
)
async def get_current_admin_profile(
    current_admin: dict = Depends(get_current_admin), db: AsyncSession = Depends(get_db)
):
    """
    Get the current admin's profile information.
    """
    auth_service = AdminAuthService(db)
    admin = await auth_service.get_admin_by_id(current_admin["id"])

    if not admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin not found")

    return api_response(
        data=auth_service.admin_to_response(admin),
        message="Admin profile retrieved successfully",
        status_code=status.HTTP_200_OK,
    )


@router.put(
    "/change-password",
    status_code=status.HTTP_200_OK,
    summary="Change admin password",
)
async def change_admin_password(
    password_data: AdminPasswordChangeRequest,
    current_admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Change the current admin's password.
    """
    auth_service = AdminAuthService(db)

    await auth_service.change_password(admin_id=current_admin["id"], password_data=password_data)

    return api_response(
        data={},
        message="Password changed successfully",
        status_code=status.HTTP_200_OK,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Logout admin",
)
async def logout_admin(current_admin: dict = Depends(get_current_admin)):
    """
    Logout an admin. In a stateless JWT setup, this mainly serves as a client-side signal.
    The client should discard the token.
    """
    return api_response(
        data={},
        message="Admin logout successful",
        status_code=status.HTTP_200_OK,
    )
