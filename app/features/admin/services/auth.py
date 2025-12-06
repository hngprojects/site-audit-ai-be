from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.admin.models.admin import Admin
from app.features.admin.schemas.auth import (
    AdminLoginRequest,
    AdminPasswordChangeRequest,
    AdminRegistrationRequest,
    AdminResponse,
)
from app.features.auth.utils.security import create_access_token, hash_password, verify_password
from app.platform.config import settings


class AdminAuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return verify_password(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        return hash_password(password)

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None):
        return create_access_token(data, expires_delta)

    async def get_admin_by_email(self, email: str) -> Optional[Admin]:
        result = await self.db.execute(select(Admin).where(Admin.email == email.lower()))
        return result.scalar_one_or_none()

    async def authenticate_admin(self, email: str, password: str) -> Optional[Admin]:
        admin = await self.get_admin_by_email(email)
        if not admin:
            return None
        if not self.verify_password(password, admin.password_hash):  # type: ignore
            return None
        if not bool(admin.is_active):
            return None
        return admin

    async def create_admin(
        self, admin_data: AdminRegistrationRequest, created_by: Optional[str] = None
    ) -> Admin:
        existing_admin = await self.get_admin_by_email(admin_data.email)
        if existing_admin:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Admin with this email already exists",
            )

        admin = Admin(
            email=admin_data.email.lower(),
            password_hash=self.get_password_hash(admin_data.password),
            is_super_admin=admin_data.is_super_admin,
            created_by=created_by,
        )

        self.db.add(admin)
        await self.db.commit()
        await self.db.refresh(admin)
        return admin

    async def login_admin(self, login_data: AdminLoginRequest) -> tuple[Admin, str]:
        admin = await self.authenticate_admin(login_data.email, login_data.password)
        if not admin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = self.create_access_token(
            data={"sub": str(admin.id), "email": admin.email, "is_admin": True},
            expires_delta=access_token_expires,
        )

        admin.last_login = datetime.utcnow()
        await self.db.commit()

        return admin, access_token

    async def change_password(
        self, admin_id: str, password_data: AdminPasswordChangeRequest
    ) -> bool:
        admin = await self.db.get(Admin, admin_id)
        if not admin:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin not found")

        if not self.verify_password(password_data.current_password, str(admin.password_hash)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect"
            )

        admin.password_hash = self.get_password_hash(password_data.new_password)  # type: ignore
        await self.db.commit()
        return True

    async def get_admin_by_id(self, admin_id: str) -> Optional[Admin]:
        return await self.db.get(Admin, admin_id)

    @staticmethod
    def admin_to_response(admin: Admin) -> AdminResponse:
        return AdminResponse(
            id=str(admin.id),
            email=admin.email,
            is_active=admin.is_active,
            is_super_admin=admin.is_super_admin,
            last_login=admin.last_login.isoformat() if admin.last_login else None,
            created_at=admin.created_at.isoformat(),
        )
